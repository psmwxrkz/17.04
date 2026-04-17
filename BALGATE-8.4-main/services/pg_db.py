import psycopg
from psycopg.rows import dict_row
from datetime import datetime, timedelta


class PostgresDatabase:
    def __init__(self):
        self.conn_params = {
            "host": "172.28.43.147",   # ex: 192.168.1.10
            "dbname": "balgate",
            "user": "balgate_user",
            "password": "shxrkzeqnx10",
            "port": 5432,
        }

        # Garante que a tabela existe
        self._inicializar()

    # ------------------------------------------------------------------
    # CONEXÃO
    # ------------------------------------------------------------------
    def _conectar(self):
        return psycopg.connect(
            **self.conn_params,
            row_factory=dict_row
        )
        
    # ------------------------------------------------------------------
    # CRIA TABELA SE NÃO EXISTIR
    # ------------------------------------------------------------------
    def _inicializar(self):
        sql = """
        CREATE TABLE IF NOT EXISTS controle_fichas (
            origem TEXT NOT NULL,
            registro_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendente',
            concluido_em_local TIMESTAMP,
            ultimo_visto_em TIMESTAMP,
            criado_em TIMESTAMP NOT NULL,
            atualizado_em TIMESTAMP NOT NULL,
            PRIMARY KEY (origem, registro_id)
        );
        """

        with self._conectar() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    # ------------------------------------------------------------------
    # UPSERT (INSERT OU UPDATE)
    # ------------------------------------------------------------------
    def upsert_ficha(self, origem, registro_id, status, concluido_em_local=None):
        agora = datetime.now()

        sql = """
        INSERT INTO controle_fichas (
            origem,
            registro_id,
            status,
            concluido_em_local,
            ultimo_visto_em,
            criado_em,
            atualizado_em
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (origem, registro_id)
        DO UPDATE SET
            status = EXCLUDED.status,
            concluido_em_local = 
                CASE
                    WHEN EXCLUDED.status = 'realizado'
                         AND controle_fichas.concluido_em_local IS NULL
                    THEN EXCLUDED.concluido_em_local
                    WHEN EXCLUDED.status = 'pendente'
                    THEN NULL
                    ELSE controle_fichas.concluido_em_local
                END,
            ultimo_visto_em = EXCLUDED.ultimo_visto_em,
            atualizado_em = EXCLUDED.atualizado_em;
        """

        with self._conectar() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    origem,
                    str(registro_id),
                    status,
                    concluido_em_local,
                    agora,
                    agora,
                    agora,
                ))
            conn.commit()

    # ------------------------------------------------------------------
    # OBTÉM DATA DE CONCLUSÃO LOCAL
    # ------------------------------------------------------------------
    def obter_conclusao_local(self, origem, registro_id):
        sql = """
        SELECT concluido_em_local
        FROM controle_fichas
        WHERE origem = %s AND registro_id = %s
        """

        with self._conectar() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (origem, str(registro_id)))
                row = cur.fetchone()

        if not row:
            return None

        dt = row.get("concluido_em_local")
        return dt.isoformat() if dt else None

    # ------------------------------------------------------------------
    # VERIFICA SE A FICHA EXPIROU
    # ------------------------------------------------------------------
    def ficha_expirada(self, origem, registro_id, horas=24):
        concluido_em_local = self.obter_conclusao_local(origem, registro_id)
        if not concluido_em_local:
            return False

        try:
            dt = datetime.fromisoformat(concluido_em_local)
        except Exception:
            return False

        limite = datetime.now() - timedelta(hours=horas)
        return dt <= limite

    # ------------------------------------------------------------------
    # REMOVE FICHAS EXPIRADAS
    # ------------------------------------------------------------------
    def remover_expiradas(self, horas=24):
        limite = datetime.now() - timedelta(hours=horas)

        sql = """
        DELETE FROM controle_fichas
        WHERE status = 'realizado'
          AND concluido_em_local IS NOT NULL
          AND concluido_em_local <= %s
        """

        with self._conectar() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (limite,))
                removidos = cur.rowcount
            conn.commit()

        return removidos