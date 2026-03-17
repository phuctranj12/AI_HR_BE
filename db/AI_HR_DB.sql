-- ============================================================
--  DATABASE : employee_management
--  Encoding : utf8mb4 / utf8mb4_unicode_ci
--  Engine   : InnoDB
--
--  Table map  (Vietnamese → English)
--  ─────────────────────────────────────────────
--  Trang_thai        →  statuses
--  Loại giấy tờ     →  document_types
--  Nhân viên         →  employees
--  Giấy tờ           →  documents
--  Du an             →  projects
--  Du_an_NV          →  project_employees
--  Yêu cầu dự án    →  project_requirements
-- ============================================================

CREATE DATABASE IF NOT EXISTS employee_management
    CHARACTER SET  utf8mb4
    COLLATE        utf8mb4_unicode_ci;

USE employee_management;

-- ============================================================
--  0. DISABLE FK CHECKS DURING CREATION (re-enabled at end)
-- ============================================================
SET FOREIGN_KEY_CHECKS = 0;


-- ============================================================
--  TABLE 1 : statuses   (Trang_thai)
--  Master list of status values shared across the system.
--  Both employees and documents reference this table.
-- ============================================================
CREATE TABLE statuses (
    id          INT(10)      NOT NULL AUTO_INCREMENT COMMENT 'PK',
    status_name VARCHAR(255) NOT NULL               COMMENT 'ten — Human-readable status label',

    PRIMARY KEY (id),
    UNIQUE KEY uq_status_name (status_name)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Trang_thai — Shared status lookup table';

-- Seed data (adjust values to match your business rules)
INSERT INTO statuses (status_name) VALUES
    ('Active'),
    ('Inactive'),
    ('On Leave'),
    ('Terminated'),
    ('Valid'),
    ('Expired'),
    ('AboutToExpired'),
    ('Pending'),
    ('Revoked'),
    ('Planning'),
    ('Completed'),
    ('Cancelled');


-- ============================================================
--  TABLE 2 : document_types   (Loại giấy tờ)
--  Master list of official document categories.
-- ============================================================
CREATE TABLE document_types (
    id        INT(10)      NOT NULL AUTO_INCREMENT COMMENT 'PK',
    type_name VARCHAR(255) NOT NULL               COMMENT 'loai_giay_to',

    PRIMARY KEY (id),
    UNIQUE KEY uq_type_name (type_name)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Loại giấy tờ — Document type master';


-- ============================================================
--  TABLE 3 : employees   (Nhân viên)
--  Core employee records.
--  status_id FK → statuses (replaces inline trang_thai varchar)
-- ============================================================
CREATE TABLE employees (
    id                INT(10)      NOT NULL AUTO_INCREMENT           COMMENT 'PK',
    full_name         VARCHAR(255) NOT NULL                          COMMENT 'ho_ten',
    employee_code     VARCHAR(255)                                   COMMENT 'ma_nhan_vien — Unique employee code (N + U in diagram)',
    date_of_birth     DATE                                           COMMENT 'ngay_sinh',
    hometown          VARCHAR(255)                                   COMMENT 'que_quan',
    join_date         DATE                                           COMMENT 'ngay_check_in — N in diagram',
    department        VARCHAR(255)                                   COMMENT 'bo_phan — N in diagram',
    phone             VARCHAR(20)                                    COMMENT 'sdt — N in diagram; VARCHAR(20) sufficient for international format',
    email             VARCHAR(255)                                  COMMENT 'email — N in diagram',
    permanent_address VARCHAR(500)                                   COMMENT 'dia_chi_thuong_tru — Extended to 500 chars',
    folder_path       VARCHAR(500)                                   COMMENT 'duong_dan_luu_folder',
    position          VARCHAR(255)                                   COMMENT 'chuc_vu — N in diagram',
    file_path         VARCHAR(500)                                   COMMENT 'file_path',
    created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                                                     COMMENT 'create_at — Fixed: diagram shows DATE; TIMESTAMP is correct',
    updated_at        TIMESTAMP    NULL DEFAULT CURRENT_TIMESTAMP
                                           ON UPDATE CURRENT_TIMESTAMP
                                                                     COMMENT 'update_at — N in diagram',
    notes             TEXT                                           COMMENT 'ghi_chu — N in diagram; TEXT allows > 255 chars',
    status_id         INT(10)                                        COMMENT 'Trang_thaiid — FK to statuses (new in v2)',

    PRIMARY KEY (id),
    UNIQUE KEY uq_employee_code (employee_code),
    KEY idx_emp_status     (status_id),
    KEY idx_emp_department (department),
    KEY idx_emp_join_date  (join_date),

    CONSTRAINT fk_emp_status
        FOREIGN KEY (status_id)
        REFERENCES statuses (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Nhân viên — Employee master records';


-- ============================================================
--  TABLE 4 : documents   (Giấy tờ)
--  Official documents belonging to employees.
--  Now has proper PK (id) — was missing in v1 diagram.
--  Both document_type_id and status_id are FK lookups.
-- ============================================================
CREATE TABLE documents (
    id               INT(10)      NOT NULL AUTO_INCREMENT            COMMENT 'PK — Added; diagram v2 now shows id correctly',
    document_name    VARCHAR(255)                                    COMMENT 'ten_giay_to',
    issued_date      DATE                                            COMMENT 'ngay-cap — Fixed: was VARCHAR(255) with typo dash; changed to DATE',
    issued_by        VARCHAR(255)                                    COMMENT 'noi_cap — N in diagram',
    start_date       DATE                                            COMMENT 'ngay_bat_dau — N in diagram; already DATE in v2',
    end_date         DATE                                            COMMENT 'ngay_ket_thuc — N in diagram; already DATE in v2',
    document_number  VARCHAR(255)                                    COMMENT 'ma_so — N in diagram',
    notes            TEXT                                            COMMENT 'note — N in diagram; TEXT for long content',
    document_type_id INT(10)                                         COMMENT 'Loai_giay_to_id — FK to document_types',
    employee_id      INT(10)                                         COMMENT 'Nhan_vien_id — FK to employees',
    file_path        VARCHAR(500)                                    COMMENT 'file_path — Scanned copy path',
    status_id        INT(10)                                         COMMENT 'Trang_thaiid — FK to statuses (new in v2)',

    PRIMARY KEY (id),
    KEY idx_doc_employee   (employee_id),
    KEY idx_doc_type       (document_type_id),
    KEY idx_doc_status     (status_id),
    KEY idx_doc_number     (document_number),
    KEY idx_doc_dates      (start_date, end_date),

    CONSTRAINT fk_doc_employee
        FOREIGN KEY (employee_id)
        REFERENCES employees (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_doc_type
        FOREIGN KEY (document_type_id)
        REFERENCES document_types (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_doc_status
        FOREIGN KEY (status_id)
        REFERENCES statuses (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Giấy tờ — Employee official documents';


-- ============================================================
--  TABLE 5 : projects   (Du an)
--  Project master records.
--  [v2.1] trang_thai VARCHAR → status_id INT FK → statuses
--  Now consistent with employees and documents tables.
-- ============================================================
CREATE TABLE projects (
    id           INT(10)      NOT NULL AUTO_INCREMENT                COMMENT 'PK',
    project_name VARCHAR(255)                                COMMENT 'ten',
    location     VARCHAR(255)                                        COMMENT 'dia_diem',
    function     VARCHAR(255)                                        COMMENT 'chuc_nang_du_an — Purpose of the project',
    scale        VARCHAR(255)                                        COMMENT 'quy_mo_du_an — Project scale description',
    start_date   DATE                                                COMMENT 'ngay_bat_dau',
    end_date     DATE                                                COMMENT 'ngay_ket_thuc',
    status_id    INT(10)                                    COMMENT 'trang_thai — FK to statuses (updated v2.1)',
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP     COMMENT 'create_at — Fixed: diagram shows DATE; TIMESTAMP is correct',
    updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                                       ON UPDATE CURRENT_TIMESTAMP   COMMENT 'update_at',

    PRIMARY KEY (id),
    KEY idx_proj_status (status_id),
    KEY idx_proj_dates  (start_date, end_date),

    CONSTRAINT fk_proj_status
        FOREIGN KEY (status_id)
        REFERENCES statuses (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Du an — Project master records';


-- ============================================================
--  TABLE 6 : project_employees   (Du_an_NV)
--  Junction: many employees ↔ many projects.
--  Composite PK on (employee_id, project_id).
-- ============================================================
CREATE TABLE project_employees (
    employee_id INT(10)      NOT NULL                                COMMENT 'Nhan_vien_id — FK to employees',
    project_id  INT(10)      NOT NULL                                COMMENT 'Du_an_id — FK to projects',
    role        VARCHAR(255)                                         COMMENT 'chuc_vu — Employee role within this project',
    start_date  DATE         NOT NULL                                COMMENT 'ngay_bat_dau',
    end_date    DATE                                                 COMMENT 'ngay_ket_thuc — N in diagram; NULL = currently active',

    PRIMARY KEY (employee_id, project_id),
    KEY idx_pe_project (project_id),
    KEY idx_pe_dates   (start_date, end_date),

    CONSTRAINT fk_pe_employee
        FOREIGN KEY (employee_id)
        REFERENCES employees (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_pe_project
        FOREIGN KEY (project_id)
        REFERENCES projects (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Du_an_NV — Employee–project assignment (M:N junction)';


-- ============================================================
--  TABLE 7 : project_requirements   (Yêu cầu dự án)
--  Which document types are required for a given project.
--  Composite PK on (project_id, document_type_id).
-- ============================================================
CREATE TABLE project_requirements (
    project_id       INT(10) NOT NULL                                COMMENT 'Du_an_id — FK to projects',
    document_type_id INT(10) NOT NULL                                COMMENT 'Loai_giay_to_id — FK to document_types',

    PRIMARY KEY (project_id, document_type_id),
    KEY idx_pr_doctype (document_type_id),

    CONSTRAINT fk_pr_project
        FOREIGN KEY (project_id)
        REFERENCES projects (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_pr_doctype
        FOREIGN KEY (document_type_id)
        REFERENCES document_types (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Yêu cầu dự án — Required document types per project';


-- ============================================================
--  Bật kiểm tra khoá ngoại để bảo vệ dữ liệu . Khi migration dữ liệu thì set về 0 
-- ============================================================
SET FOREIGN_KEY_CHECKS = 1;


