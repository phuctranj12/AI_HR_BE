def init_schema(conn) -> None:
    """Create core tables compatible with db/AI_HR_DB.sql (Postgres version).

    The shipped AI_HR_DB.sql file is MySQL-flavored; this function creates an
    equivalent schema in Postgres (id/relations/unique constraints).
    """
    with conn.cursor() as cur:
        # statuses
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS statuses (
                id SERIAL PRIMARY KEY,
                status_name TEXT NOT NULL UNIQUE
            );
            """
        )

        # document_types
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS document_types (
                id SERIAL PRIMARY KEY,
                type_name TEXT NOT NULL UNIQUE
            );
            """
        )

        # employees (subset used by this app)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                full_name TEXT NOT NULL,
                employee_code TEXT UNIQUE,
                date_of_birth DATE,
                hometown TEXT,
                join_date DATE,
                department TEXT,
                phone TEXT,
                email TEXT,
                permanent_address TEXT,
                folder_path TEXT,
                position TEXT,
                file_path TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                status_id INTEGER REFERENCES statuses(id) ON UPDATE CASCADE ON DELETE RESTRICT
            );
            """
        )

        # documents (subset used by this app)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                document_name TEXT,
                issued_date DATE,
                issued_by TEXT,
                start_date DATE,
                end_date DATE,
                document_number TEXT,
                notes TEXT,
                document_type_id INTEGER REFERENCES document_types(id) ON UPDATE CASCADE ON DELETE RESTRICT,
                employee_id INTEGER REFERENCES employees(id) ON UPDATE CASCADE ON DELETE RESTRICT,
                file_path TEXT,
                status_id INTEGER REFERENCES statuses(id) ON UPDATE CASCADE ON DELETE RESTRICT
            );
            """
        )

        # projects
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                project_name TEXT,
                location TEXT,
                function TEXT,
                scale TEXT,
                start_date DATE,
                end_date DATE,
                status_id INTEGER REFERENCES statuses(id) ON UPDATE CASCADE ON DELETE RESTRICT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # project_employees (M:N)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS project_employees (
                employee_id INTEGER NOT NULL REFERENCES employees(id) ON UPDATE CASCADE ON DELETE RESTRICT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON UPDATE CASCADE ON DELETE RESTRICT,
                role TEXT,
                start_date DATE NOT NULL,
                end_date DATE,
                PRIMARY KEY (employee_id, project_id)
            );
            """
        )

        # project_requirements (required doc types per project)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS project_requirements (
                project_id INTEGER NOT NULL REFERENCES projects(id) ON UPDATE CASCADE ON DELETE CASCADE,
                document_type_id INTEGER NOT NULL REFERENCES document_types(id) ON UPDATE CASCADE ON DELETE RESTRICT,
                PRIMARY KEY (project_id, document_type_id)
            );
            """
        )

        # updated_at trigger for employees
        cur.execute(
            """
            CREATE OR REPLACE FUNCTION set_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        cur.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = 'employees_set_updated_at'
                ) THEN
                    CREATE TRIGGER employees_set_updated_at
                    BEFORE UPDATE ON employees
                    FOR EACH ROW
                    EXECUTE FUNCTION set_updated_at();
                END IF;
            END$$;
            """
        )

        # Seed statuses if empty
        cur.execute("SELECT COUNT(*) FROM statuses;")
        (cnt,) = cur.fetchone()
        if cnt == 0:
            cur.execute(
                """
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
                    ('Cancelled')
                ON CONFLICT DO NOTHING;
                """
            )

    conn.commit()

