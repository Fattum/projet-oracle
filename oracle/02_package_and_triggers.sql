-- =============================================================================
-- Package + triggers métier (cohérence absences / quotas / alertes)
-- Exécuter après 01_tables_sequences.sql
-- =============================================================================

CREATE OR REPLACE PACKAGE PKG_GESTION_ABSENCES AS
    /** Nombre d'absences non justifiées pour (étudiant, cours, année). */
    FUNCTION F_NB_ABSENCES_NON_JUST(
        p_id_etudiant IN NUMBER,
        p_id_cours    IN NUMBER,
        p_id_annee    IN NUMBER
    ) RETURN NUMBER;

    /** Seuil : PARAM_COURS_SEUIL sinon PARAM_GLOBAL_ANNEE sinon 3. */
    FUNCTION F_SEUIL_NON_JUSTIF(
        p_id_cours IN NUMBER,
        p_id_annee IN NUMBER
    ) RETURN NUMBER;

    /**
     * Enregistre une absence dans une transaction unique (INSERT).
     * Lève une exception si incohérence cours/année ou étudiant inactif.
     */
    PROCEDURE P_ENREGISTRER_ABSENCE(
        p_id_inscription IN NUMBER,
        p_id_seance      IN NUMBER,
        p_motif          IN VARCHAR2,
        p_justifiee      IN CHAR,
        p_id_absence     OUT NUMBER
    );

    /**
     * Mise à jour justification / motif (scolarité). Déclenche les triggers
     * de quota (réévaluation si passage N→O ou O→N).
     */
    PROCEDURE P_MAJ_ABSENCE_JUSTIF(
        p_id_absence IN NUMBER,
        p_justifiee  IN CHAR,
        p_motif      IN VARCHAR2
    );
END PKG_GESTION_ABSENCES;
/

CREATE OR REPLACE PACKAGE BODY PKG_GESTION_ABSENCES AS

    /**
     * Compte les absences non justifiees (etat COMMIT de la base).
     * PRAGMA AUTONOMOUS_TRANSACTION : obligatoire car appelee depuis le trigger
     * TRG_ABSENCE_AIUD_QUOTA ; sans cela ORA-04091 (table ABSENCE en mutation).
     */
    FUNCTION F_NB_ABSENCES_NON_JUST(
        p_id_etudiant IN NUMBER,
        p_id_cours    IN NUMBER,
        p_id_annee    IN NUMBER
    ) RETURN NUMBER IS
        PRAGMA AUTONOMOUS_TRANSACTION;
        v_cnt NUMBER;
    BEGIN
        SELECT COUNT(*)
        INTO v_cnt
        FROM ABSENCE A
        JOIN INSCRIPTION I ON I.ID_INSCRIPTION = A.ID_INSCRIPTION
        WHERE I.ID_ETUDIANT = p_id_etudiant
          AND I.ID_COURS = p_id_cours
          AND I.ID_ANNEE = p_id_annee
          AND I.STATUT_INSC = 'VALIDEE'
          AND A.JUSTIFIEE = 'N';
        COMMIT; /* termine la transaction autonome (lecture seule) */
        RETURN v_cnt;
    END F_NB_ABSENCES_NON_JUST;

    FUNCTION F_SEUIL_NON_JUSTIF(
        p_id_cours IN NUMBER,
        p_id_annee IN NUMBER
    ) RETURN NUMBER IS
        v_s NUMBER;
    BEGIN
        BEGIN
            SELECT SEUIL_NON_JUSTIF INTO v_s
            FROM PARAM_COURS_SEUIL
            WHERE ID_COURS = p_id_cours AND ID_ANNEE = p_id_annee;
            RETURN v_s;
        EXCEPTION
            WHEN NO_DATA_FOUND THEN NULL;
        END;
        BEGIN
            SELECT SEUIL_NON_JUSTIF INTO v_s
            FROM PARAM_GLOBAL_ANNEE
            WHERE ID_ANNEE = p_id_annee;
            RETURN v_s;
        EXCEPTION
            WHEN NO_DATA_FOUND THEN
                RETURN 3;
        END;
    END F_SEUIL_NON_JUSTIF;

    PROCEDURE P_ENREGISTRER_ABSENCE(
        p_id_inscription IN NUMBER,
        p_id_seance      IN NUMBER,
        p_motif          IN VARCHAR2,
        p_justifiee      IN CHAR,
        p_id_absence     OUT NUMBER
    ) IS
        v_id_etu NUMBER;
        v_ins_cours NUMBER;
        v_ins_annee NUMBER;
        v_sea_cours NUMBER;
        v_sea_annee NUMBER;
        v_statut VARCHAR2(20);
    BEGIN
        IF p_justifiee NOT IN ('O', 'N') THEN
            RAISE_APPLICATION_ERROR(-20001, 'JUSTIFIEE doit etre O ou N');
        END IF;

        SELECT ID_ETUDIANT, ID_COURS, ID_ANNEE
        INTO v_id_etu, v_ins_cours, v_ins_annee
        FROM INSCRIPTION
        WHERE ID_INSCRIPTION = p_id_inscription
        FOR UPDATE;

        SELECT STATUT INTO v_statut FROM ETUDIANT WHERE ID_ETUDIANT = v_id_etu;
        IF v_statut <> 'ACTIF' THEN
            RAISE_APPLICATION_ERROR(-20002, 'Etudiant non actif : inscription impossible');
        END IF;

        SELECT ID_COURS, ID_ANNEE
        INTO v_sea_cours, v_sea_annee
        FROM SEANCE
        WHERE ID_SEANCE = p_id_seance;

        IF v_ins_cours <> v_sea_cours OR v_ins_annee <> v_sea_annee THEN
            RAISE_APPLICATION_ERROR(-20003,
                'Seance et inscription incoherentes (cours ou annee differents)');
        END IF;

        INSERT INTO ABSENCE (ID_ABSENCE, ID_INSCRIPTION, ID_SEANCE, MOTIF, JUSTIFIEE)
        VALUES (NULL, p_id_inscription, p_id_seance, p_motif, p_justifiee)
        RETURNING ID_ABSENCE INTO p_id_absence;
    END P_ENREGISTRER_ABSENCE;

    PROCEDURE P_MAJ_ABSENCE_JUSTIF(
        p_id_absence IN NUMBER,
        p_justifiee  IN CHAR,
        p_motif      IN VARCHAR2
    ) IS
    BEGIN
        IF p_justifiee NOT IN ('O', 'N') THEN
            RAISE_APPLICATION_ERROR(-20004, 'JUSTIFIEE doit etre O ou N');
        END IF;

        UPDATE ABSENCE
        SET JUSTIFIEE = p_justifiee,
            MOTIF = p_motif
        WHERE ID_ABSENCE = p_id_absence;

        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20005, 'Absence introuvable');
        END IF;
    END P_MAJ_ABSENCE_JUSTIF;

END PKG_GESTION_ABSENCES;
/

-- -----------------------------------------------------------------------------
-- Trigger : inscription réservée aux étudiants ACTIF
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER TRG_INSCRIPTION_BI_ETU
BEFORE INSERT OR UPDATE OF ID_ETUDIANT ON INSCRIPTION
FOR EACH ROW
DECLARE
    v_statut VARCHAR2(20);
BEGIN
    SELECT STATUT INTO v_statut FROM ETUDIANT WHERE ID_ETUDIANT = :NEW.ID_ETUDIANT;
    IF v_statut <> 'ACTIF' THEN
        RAISE_APPLICATION_ERROR(-20010,
            'Inscription refusee : statut etudiant doit etre ACTIF');
    END IF;
END;
/

-- -----------------------------------------------------------------------------
-- Trigger : cohérence absence / séance / inscription (même cours, même année)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER TRG_ABSENCE_BI_VALID
BEFORE INSERT OR UPDATE OF ID_INSCRIPTION, ID_SEANCE ON ABSENCE
FOR EACH ROW
DECLARE
    v_ins_c NUMBER;
    v_ins_a NUMBER;
    v_sea_c NUMBER;
    v_sea_a NUMBER;
    v_st    VARCHAR2(20);
BEGIN
    SELECT ID_COURS, ID_ANNEE INTO v_ins_c, v_ins_a
    FROM INSCRIPTION WHERE ID_INSCRIPTION = :NEW.ID_INSCRIPTION;

    SELECT ID_COURS, ID_ANNEE INTO v_sea_c, v_sea_a
    FROM SEANCE WHERE ID_SEANCE = :NEW.ID_SEANCE;

    IF v_ins_c <> v_sea_c OR v_ins_a <> v_sea_a THEN
        RAISE_APPLICATION_ERROR(-20011,
            'Absence : cours ou annee different entre inscription et seance');
    END IF;

    SELECT STATUT_INSC INTO v_st FROM INSCRIPTION WHERE ID_INSCRIPTION = :NEW.ID_INSCRIPTION;
    IF v_st <> 'VALIDEE' THEN
        RAISE_APPLICATION_ERROR(-20012, 'Absence : inscription non validee');
    END IF;

    SELECT STATUT_SEANCE INTO v_st FROM SEANCE WHERE ID_SEANCE = :NEW.ID_SEANCE;
    IF v_st = 'ANNULEE' THEN
        RAISE_APPLICATION_ERROR(-20013, 'Absence : seance annulee');
    END IF;
END;
/

-- -----------------------------------------------------------------------------
-- Trigger : alerte quota (transition franchissement du seuil)
-- F_NB_ABSENCES_NON_JUST est autonome : ne voit pas la ligne en cours d'INSERT/UPDATE.
-- On recalcule v_cnt / v_prev explicitement pour INSERT N et UPDATE O<->N.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER TRG_ABSENCE_AIUD_QUOTA
AFTER INSERT OR UPDATE OF JUSTIFIEE ON ABSENCE
FOR EACH ROW
DECLARE
    v_etu NUMBER;
    v_cours NUMBER;
    v_annee NUMBER;
    v_seuil NUMBER;
    v_base NUMBER;
    v_cnt NUMBER;
    v_prev NUMBER;
    v_msg VARCHAR2(500);
    v_code_cours VARCHAR2(50);
    v_lib_annee VARCHAR2(200);
BEGIN
    IF INSERTING AND :NEW.JUSTIFIEE = 'O' THEN
        RETURN;
    END IF;
    IF UPDATING AND :NEW.JUSTIFIEE = 'O' AND NVL(:OLD.JUSTIFIEE, 'X') = 'O' THEN
        RETURN;
    END IF;

    SELECT I.ID_ETUDIANT, I.ID_COURS, I.ID_ANNEE
    INTO v_etu, v_cours, v_annee
    FROM INSCRIPTION I
    WHERE I.ID_INSCRIPTION = :NEW.ID_INSCRIPTION;

    v_seuil := PKG_GESTION_ABSENCES.F_SEUIL_NON_JUSTIF(v_cours, v_annee);
    v_base := PKG_GESTION_ABSENCES.F_NB_ABSENCES_NON_JUST(v_etu, v_cours, v_annee);

    IF INSERTING AND :NEW.JUSTIFIEE = 'N' THEN
        v_cnt := v_base + 1;
        v_prev := v_base;
    ELSIF UPDATING THEN
        IF :NEW.JUSTIFIEE = 'N' AND NVL(:OLD.JUSTIFIEE, 'X') = 'O' THEN
            v_cnt := v_base + 1;
            v_prev := v_base;
        ELSIF :NEW.JUSTIFIEE = 'O' AND :OLD.JUSTIFIEE = 'N' THEN
            v_cnt := v_base - 1;
            v_prev := v_base;
        ELSE
            v_cnt := v_base;
            v_prev := v_base;
        END IF;
    END IF;

    IF :NEW.JUSTIFIEE = 'N' AND v_cnt >= v_seuil AND NVL(v_prev, 0) < v_seuil THEN
        BEGIN
            SELECT C.CODE_COURS, A.LIBELLE
            INTO v_code_cours, v_lib_annee
            FROM COURS C, ANNEE_UNIV A
            WHERE C.ID_COURS = v_cours AND A.ID_ANNEE = v_annee;
        EXCEPTION
            WHEN NO_DATA_FOUND THEN
                v_code_cours := 'ID' || v_cours;
                v_lib_annee := 'ID' || v_annee;
        END;
        v_msg := 'Quota atteint : ' || v_cnt || ' absence(s) non justifiee(s) (seuil ' ||
                 v_seuil || ') pour cours ' || v_code_cours || ' / annee ' || v_lib_annee;
        INSERT INTO HISTORIQUE_ALERTE (
            ID_ALERTE, ID_ETUDIANT, ID_COURS, ID_ANNEE, NB_ABS_NON_JUST, MESSAGE
        ) VALUES (
            NULL, v_etu, v_cours, v_annee, v_cnt, v_msg
        );
    END IF;
END;
/

-- -----------------------------------------------------------------------------
-- Trigger : empêcher modification structurante d'une séance ayant des absences
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER TRG_SEANCE_BU
BEFORE UPDATE OF ID_COURS, ID_ANNEE, DATE_SEANCE, HEURE_DEBUT, HEURE_FIN ON SEANCE
FOR EACH ROW
WHEN (
    OLD.ID_COURS    <> NEW.ID_COURS OR
    OLD.ID_ANNEE    <> NEW.ID_ANNEE OR
    OLD.DATE_SEANCE <> NEW.DATE_SEANCE OR
    OLD.HEURE_DEBUT <> NEW.HEURE_DEBUT OR
    OLD.HEURE_FIN   <> NEW.HEURE_FIN
)
DECLARE
    v_n NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_n FROM ABSENCE WHERE ID_SEANCE = :OLD.ID_SEANCE;
    IF v_n > 0 THEN
        RAISE_APPLICATION_ERROR(-20020,
            'Modification seance interdite : absences deja enregistrees');
    END IF;
END;
/
