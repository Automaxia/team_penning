import os
import psycopg2, json
import shutil, traceback
from dotenv import dotenv_values

class Configuracao():

    def __init__(self):
      try:
        config = dotenv_values(".env")
        self.config = json.loads((json.dumps(config) ))

        self.create_database()
        os.system("alembic init alembic")
        shutil.copy('env_alembic.py', 'alembic/env.py')
        os.system('alembic revision --autogenerate -m "Criando a base de dados"')
        os.system('alembic upgrade head')

        self.conecta_db()
      except Exception as erro:
        shutil.copy('env_alembic.py', 'alembic/env.py')
        print(erro)

    def create_database(self):
        """Create the database and set up user permissions"""
        try:
            # Connect to postgres database to create our database
            conn = psycopg2.connect(
                host=self.config["HOST"],
                port=self.config["PORT"],
                database='postgres',  # Connect to default postgres database
                user='postgres',
                password='2tt7fyViaTspqMr1'
            )
            conn.autocommit = True  # Needed for creating database
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'teampenning'")
            exists = cursor.fetchone()
            
            if not exists:
                print("Creating database 'teampenning'...")
                # Create database
                cursor.execute("CREATE DATABASE teampenning")
                
                # Close connection to postgres database
                cursor.close()
                conn.close()
                
                # Connect to the new database using our existing method
                self.conecta_db()
                
                # Set autocommit for schema operations
                self.con.autocommit = True
                
                # Grant permissions to current user
                self.cur.execute(f"CREATE ROLE usr_team WITH LOGIN PASSWORD '2tt7fyViaTspq$14U';")
                self.cur.execute(f"ALTER DATABASE teampenning OWNER TO usr_team")
                self.cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE teampenning TO usr_team")
                self.cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE teampenning TO postgres")
                self.cur.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO usr_team")
                self.cur.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO usr_team")
                self.cur.execute(f"ALTER ROLE usr_team SUPERUSER CREATEDB CREATEROLE INHERIT LOGIN REPLICATION BYPASSRLS;")
                
                print("Database created and permissions set successfully")

                self.cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
                self.cur.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")
                self.cur.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")
                self.cur.execute("CREATE EXTENSION IF NOT EXISTS pg_cron;")
                
                # Close this connection as it will be reopened later
                self.cur.close()
                self.con.close()
            else:
                print("Database 'teampenning' already exists")
                cursor.close()
                conn.close()
            
        except Exception as error:
            print(f"Error creating database: {error}")
            traceback.print_exc()

    def conecta_db(self):
      try:
        self.con = psycopg2.connect(host=self.config["HOST"], port=self.config["PORT"], database=self.config["DATABASE"], user=self.config["USER"], password=self.config["PASSWORD"])
        self.cur = self.con.cursor()
      except:
        print(traceback.format_exc())

    def inserir_db(self):
        try:
            # ===================================================================
            # CATEGORIAS LCTP - INSERÇÃO DAS CATEGORIAS PADRÃO
            # ===================================================================
            
            # -- Categoria BABY (até 8 anos, sorteio completo)
            sql = """
            INSERT INTO public.categorias(
                nome, tipo, descricao, handicap_max_trio, idade_max_trio,
                idade_min_individual, idade_max_individual, permite_sorteio,
                min_inscricoes_sorteio, max_inscricoes_sorteio, sorteio_completo,
                tipo_pontuacao, ativa
            ) VALUES (
                'Baby', 'baby',
                'Categoria para crianças com idade máxima de 8 anos. Todos os trios são sorteados.',
                NULL, NULL, 0, 8, true, 3, 999, true, 'contep', true
            );
            """
            self.cur.execute(sql)

            # Categoria KIDS - Jovens de 13 a 17 anos com sorteio parcial
            sql = """
            INSERT INTO public.categorias(
                nome, tipo, descricao, handicap_max_trio, idade_max_trio,
                idade_min_individual, idade_max_individual, permite_sorteio,
                min_inscricoes_sorteio, max_inscricoes_sorteio, sorteio_completo,
                tipo_pontuacao, ativa
            ) VALUES (
                'Kids', 'kids',
                'Categoria para competidores com até 10 anos em 30/11/24. Sorteio parcial com mínimo de 3 e máximo de 9 inscrições.',
                NULL, NULL, 0, 10, true, 3, 9, false, 'contep', true
            );
            """
            self.cur.execute(sql)

            # Categoria MIRIM - Limite de 36 anos por trio
            sql = """
            INSERT INTO public.categorias(
                nome, tipo, descricao, handicap_max_trio, idade_max_trio,
                idade_min_individual, idade_max_individual, permite_sorteio,
                min_inscricoes_sorteio, max_inscricoes_sorteio, sorteio_completo,
                tipo_pontuacao, ativa
            ) VALUES (
                'Mirim', 'mirim',
                'Categoria para iniciantes com até 13 anos em 30/11/24. Trio deve ter idade somada máxima de 36 anos.',
                NULL, 36, 0, 13, true, 3, 999, false, 'contep', true
            );
            """
            self.cur.execute(sql)

            # Categoria FEMININA - Exclusiva para mulheres
            sql = """
            INSERT INTO public.categorias(
                nome, tipo, descricao, handicap_max_trio, idade_max_trio,
                idade_min_individual, idade_max_individual, permite_sorteio,
                min_inscricoes_sorteio, max_inscricoes_sorteio, sorteio_completo,
                tipo_pontuacao, ativa
            ) VALUES (
                'Feminina', 'feminina',
                'Categoria exclusiva para competidoras do sexo feminino. Sorteio parcial com até 9 competidoras sorteadas.',
                4, NULL, NULL, NULL, true, 3, 9, false, 'contep', true
            );
            """
            self.cur.execute(sql)

            # Categoria ABERTA - Sem restrições específicas
            sql = """
            INSERT INTO public.categorias(
                nome, tipo, descricao, handicap_max_trio, idade_max_trio,
                idade_min_individual, idade_max_individual, permite_sorteio,
                min_inscricoes_sorteio, max_inscricoes_sorteio, sorteio_completo,
                tipo_pontuacao, ativa
            ) VALUES (
                'Aberta', 'aberta',
                'Categoria sem restrições de idade, sexo ou handicap. Trios formados manualmente.',
                NULL, NULL, NULL, NULL, false, 3, 3, false, 'contep', true
            );
            """
            self.cur.execute(sql)

            # Categoria HANDICAP - Limite de handicap por trio
            sql = """
            INSERT INTO public.categorias(
                nome, tipo, descricao, handicap_max_trio, idade_max_trio,
                idade_min_individual, idade_max_individual, permite_sorteio,
                min_inscricoes_sorteio, max_inscricoes_sorteio, sorteio_completo,
                tipo_pontuacao, ativa
            ) VALUES (
                'Handicap', 'handicap',
                'Categoria com limite máximo de 11 pontos somados entre os três integrantes do trio.',
                11, NULL, NULL, NULL, false, 3, 3, false, 'contep', true
            );
            """
            self.cur.execute(sql)

            # ===================================================================
            # FUNÇÕES AUXILIARES DO BANCO DE DADOS
            # ===================================================================

            # Função para remover acentos
            sql = """CREATE OR REPLACE FUNCTION public.removeacento(character varying)
 RETURNS character varying
 LANGUAGE sql
 IMMUTABLE
AS $function$
SELECT TRANSLATE($1, 'áéíóúàèìòùãõâêîôôäëïöüçÁÉÍÓÚÀÈÌÒÙÃÕÂÊÎÔÛÄËÏÖÜÇ-',
'aeiouaeiouaoaeiooaeioucAEIOUAEIOUAOAEIOOAEIOUC ')
$function$
;"""
            self.cur.execute(sql)

            sql = """CREATE OR REPLACE FUNCTION public.datediff(units character varying, start_t timestamp without time zone, end_t timestamp without time zone)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
   DECLARE
     diff_interval INTERVAL;
     diff INT = 0;
     years_diff INT = 0;
   BEGIN
     IF units IN ('yy', 'yyyy', 'year', 'mm', 'm', 'month') THEN
       years_diff = DATE_PART('year', end_t) - DATE_PART('year', start_t);

       IF units IN ('yy', 'yyyy', 'year') THEN
         -- SQL Server does not count full years passed (only difference between year parts)
         RETURN years_diff;
       ELSE
         -- If end month is less than start month it will subtracted
         RETURN years_diff * 12 + (DATE_PART('month', end_t) - DATE_PART('month', start_t));
       END IF;
     END IF;

     -- Minus operator returns interval 'DDD days HH:MI:SS'
     diff_interval = end_t - start_t;

     diff = diff + DATE_PART('day', diff_interval);

     IF units IN ('wk', 'ww', 'week') THEN
       diff = diff/7;
       RETURN diff;
     END IF;

     IF units IN ('dd', 'd', 'day') THEN
       RETURN diff;
     END IF;

     diff = diff * 24 + DATE_PART('hour', diff_interval);

     IF units IN ('hh', 'hour') THEN
        RETURN diff;
     END IF;

     diff = diff * 60 + DATE_PART('minute', diff_interval);

     IF units IN ('mi', 'n', 'minute') THEN
        RETURN diff;
     END IF;

     diff = diff * 60 + DATE_PART('second', diff_interval);

     RETURN diff;
   END;
   $function$
;"""
            self.cur.execute(sql)

            sql = """CREATE VIEW vw_resumo_passadas_trio AS
SELECT 
    t.id as trio_id,
    t.numero_trio,
    t.prova_id,
    t.categoria_id,
    COUNT(p.id) as total_passadas,
    COUNT(CASE WHEN p.status = 'executada' THEN 1 END) as passadas_executadas,
    COUNT(CASE WHEN p.status = 'no_time' THEN 1 END) as passadas_no_time,
    COUNT(CASE WHEN p.status = 'pendente' THEN 1 END) as passadas_pendentes,
    AVG(CASE WHEN p.status = 'executada' THEN p.tempo_realizado END) as tempo_medio,
    MIN(CASE WHEN p.status = 'executada' THEN p.tempo_realizado END) as melhor_tempo,
    MAX(CASE WHEN p.status = 'executada' THEN p.tempo_realizado END) as pior_tempo,
    SUM(p.pontos_passada) as pontos_totais,
    MAX(p.updated_at) as ultima_atualizacao
FROM trios t
LEFT JOIN passadas_trio p ON t.id = p.trio_id
GROUP BY t.id, t.numero_trio, t.prova_id, t.categoria_id;

-- View: Controle Individual de Competidores
CREATE VIEW vw_controle_competidores AS
SELECT 
    c.id as competidor_id,
    c.nome,
    pr.id as prova_id,
    pr.nome as prova_nome,
    cat.id as categoria_id,
    cat.nome as categoria_nome,
    COALESCE(ctrl.total_passadas_executadas, 0) as total_passadas_executadas,
    COALESCE(ctrl.max_passadas_permitidas, 5) as max_passadas_permitidas,
    (COALESCE(ctrl.max_passadas_permitidas, 5) - COALESCE(ctrl.total_passadas_executadas, 0)) as passadas_restantes,
    COALESCE(ctrl.pode_competir, true) as pode_competir,
    ctrl.motivo_bloqueio
FROM competidores c
JOIN integrantes_trios it ON c.id = it.competidor_id
JOIN trios t ON it.trio_id = t.id
JOIN provas pr ON t.prova_id = pr.id
JOIN categorias cat ON t.categoria_id = cat.id
LEFT JOIN controle_participacao ctrl ON (
    c.id = ctrl.competidor_id 
    AND pr.id = ctrl.prova_id 
    AND cat.id = ctrl.categoria_id
);

-- View: Ranking por Passadas
CREATE VIEW vw_ranking_passadas AS
SELECT 
    p.id as passada_id,
    p.trio_id,
    t.numero_trio,
    p.numero_passada,
    p.tempo_realizado,
    p.pontos_passada,
    p.colocacao_passada,
    ROW_NUMBER() OVER (
        PARTITION BY p.prova_id, t.categoria_id, p.numero_passada 
        ORDER BY p.tempo_realizado ASC
    ) as ranking_tempo,
    ROW_NUMBER() OVER (
        PARTITION BY p.prova_id, t.categoria_id, p.numero_passada 
        ORDER BY p.pontos_passada DESC
    ) as ranking_pontos,
    p.prova_id,
    t.categoria_id
FROM passadas_trio p
JOIN trios t ON p.trio_id = t.id
WHERE p.status = 'executada'
ORDER BY p.prova_id, t.categoria_id, p.numero_passada, p.tempo_realizado;"""
            self.cur.execute(sql)

            sql = """
-- Trigger: Atualizar controle de participação após passada
CREATE OR REPLACE FUNCTION atualizar_controle_participacao()
RETURNS TRIGGER AS $$
BEGIN
    -- Se a passada foi executada, atualizar contadores
    IF NEW.status = 'executada' THEN
        -- Para cada integrante do trio
        INSERT INTO controle_participacao (
            competidor_id, prova_id, categoria_id, 
            total_passadas_executadas, max_passadas_permitidas
        )
        SELECT 
            it.competidor_id,
            NEW.prova_id,
            t.categoria_id,
            1,
            COALESCE(cfg.max_corridas_por_pessoa, 5)
        FROM integrantes_trios it
        JOIN trios t ON it.trio_id = t.id
        LEFT JOIN configuracao_passadas_prova cfg ON (
            t.prova_id = cfg.prova_id AND t.categoria_id = cfg.categoria_id
        )
        WHERE it.trio_id = NEW.trio_id
        ON CONFLICT (competidor_id, prova_id, categoria_id) 
        DO UPDATE SET 
            total_passadas_executadas = controle_participacao.total_passadas_executadas + 1,
            ultima_passada = NOW(),
            pode_competir = (controle_participacao.total_passadas_executadas + 1) < controle_participacao.max_passadas_permitidas,
            updated_at = NOW();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_controle_participacao
    AFTER INSERT OR UPDATE ON passadas_trio
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_controle_participacao();

-- Trigger: Atualizar resumo na tabela resultados
CREATE OR REPLACE FUNCTION atualizar_resumo_resultados()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO resultados (
        trio_id, prova_id, total_passadas, melhor_tempo, 
        pior_tempo, tempo_total, passadas_no_time, pontos_acumulados
    )
    SELECT 
        NEW.trio_id,
        NEW.prova_id,
        COUNT(*),
        MIN(CASE WHEN status = 'executada' THEN tempo_realizado END),
        MAX(CASE WHEN status = 'executada' THEN tempo_realizado END),
        SUM(CASE WHEN status = 'executada' THEN tempo_realizado ELSE 0 END),
        COUNT(CASE WHEN status = 'no_time' THEN 1 END),
        SUM(pontos_passada)
    FROM passadas_trio
    WHERE trio_id = NEW.trio_id
    ON CONFLICT (trio_id) 
    DO UPDATE SET
        total_passadas = EXCLUDED.total_passadas,
        melhor_tempo = EXCLUDED.melhor_tempo,
        pior_tempo = EXCLUDED.pior_tempo,
        tempo_total = EXCLUDED.tempo_total,
        passadas_no_time = EXCLUDED.passadas_no_time,
        pontos_acumulados = EXCLUDED.pontos_acumulados,
        media_tempo = CASE 
            WHEN EXCLUDED.total_passadas > 0 
            THEN EXCLUDED.tempo_total / EXCLUDED.total_passadas 
            ELSE NULL 
        END;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_resumo_resultados
    AFTER INSERT OR UPDATE ON passadas_trio
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_resumo_resultados();
"""
            self.cur.execute(sql)

            self.cur.execute("""-- Função para atualização automática do campo updated_at
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;""")

            self.con.commit()

            alter_system_conn = psycopg2.connect(
                host=self.config["HOST"],
                port=self.config["PORT"],
                database=self.config["DATABASE"],
                user=self.config["USER"],
                password=self.config["PASSWORD"]
            )
            alter_system_conn.autocommit = True
            alter_system_cur = alter_system_conn.cursor()

            # Execute ALTER SYSTEM commands outside of transaction block
            '''alter_system_cur.execute("ALTER SYSTEM SET pg_stat_statements.max TO 10000;")
            alter_system_cur.execute("ALTER SYSTEM SET pg_stat_statements.track TO 'all';")
            alter_system_cur.execute("ALTER SYSTEM SET max_connections = 10000;")'''

            alter_system_cur.close()
            alter_system_conn.close()
        except (Exception, psycopg2.DatabaseError) as error:
            print("Error: %s" % traceback.format_exc())
            self.con.rollback()
            self.cur.close()
            return 1
        self.cur.close()

ob = Configuracao()
retorno = ob.inserir_db()