# repositorio_usuario.py
import traceback
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from src.database import models, schemas
from src.utils.error_handler import handle_error
from src.utils.auth_utils import gerar_hash_senha, verificar_senha, gerar_token_acesso
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple
import pytz
import secrets
import string

AMSP = pytz.timezone('America/Sao_Paulo')

class RepositorioUsuario:
    
    def __init__(self, db: Session):
        self.db = db

    # ---------------------- Operações Básicas ----------------------

    async def get_by_id(self, usuario_id: int):
        """Recupera um usuário pelo ID"""
        try:
            stmt = select(schemas.Usuarios).options(
                joinedload(schemas.Usuarios.competidor)
            ).where(
                schemas.Usuarios.sq_usuario == usuario_id,
                schemas.Usuarios.bo_status == True
            )
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self.get_by_id)

    async def get_by_login(self, login: str):
        """Recupera um usuário pelo login"""
        try:
            stmt = select(schemas.Usuarios).options(
                joinedload(schemas.Usuarios.competidor)
            ).where(
                schemas.Usuarios.no_login == login.lower(),
                schemas.Usuarios.bo_status == True
            )
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self.get_by_login)

    async def get_by_email(self, email: str):
        """Recupera um usuário pelo email"""
        try:
            stmt = select(schemas.Usuarios).options(
                joinedload(schemas.Usuarios.competidor)
            ).where(
                schemas.Usuarios.no_email == email.lower(),
                schemas.Usuarios.bo_status == True
            )
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self.get_by_email)

    async def get_by_competidor_id(self, competidor_id: int):
        """Recupera um usuário pelo ID do competidor"""
        try:
            stmt = select(schemas.Usuarios).options(
                joinedload(schemas.Usuarios.competidor)
            ).where(
                schemas.Usuarios.competidor_id == competidor_id,
                schemas.Usuarios.bo_status == True
            )
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self.get_by_competidor_id)

    async def get_all(self, 
                      nome: Optional[str] = None,
                      login: Optional[str] = None,
                      email: Optional[str] = None,
                      ativo: Optional[bool] = True,
                      is_admin: Optional[bool] = None,
                      pagina: Optional[int] = 0,
                      tamanho_pagina: Optional[int] = 0):
        """Recupera usuários com filtros"""
        try:
            query = self.db.query(schemas.Usuarios).options(
                joinedload(schemas.Usuarios.competidor)
            )

            # Filtros
            if nome:
                query = query.filter(schemas.Usuarios.no_nome.ilike(f"%{nome}%"))
            if login:
                query = query.filter(schemas.Usuarios.no_login.ilike(f"%{login}%"))
            if email:
                query = query.filter(schemas.Usuarios.no_email.ilike(f"%{email}%"))
            if ativo is not None:
                query = query.filter(schemas.Usuarios.bo_status == ativo)
            if is_admin is not None:
                if is_admin:
                    query = query.filter(schemas.Usuarios.competidor_id.is_(None))
                else:
                    query = query.filter(schemas.Usuarios.competidor_id.isnot(None))

            # Ordenação
            query = query.order_by(schemas.Usuarios.no_nome)
            
            # Paginação
            if pagina > 0 and tamanho_pagina > 0:
                query = query.limit(tamanho_pagina).offset((pagina - 1) * tamanho_pagina)

            return query.all()
        except Exception as error:
            handle_error(error, self.get_all)

    async def post(self, orm: models.UsuarioPOST):
        """Cria um novo usuário"""
        try:
            # Hash da senha
            senha_hash = gerar_hash_senha(orm.no_senha)
            
            db_orm = schemas.Usuarios(
                nu_cpf=orm.nu_cpf,
                no_nome=orm.no_nome,
                no_login=orm.no_login.lower(),
                no_senha=senha_hash,
                no_email=orm.no_email.lower() if orm.no_email else None,
                no_foto=orm.no_foto,
                competidor_id=orm.competidor_id,
                bo_status=True,
                created_at=datetime.now(timezone.utc).astimezone(AMSP)
            )
            
            self.db.add(db_orm)
            self.db.commit()
            self.db.refresh(db_orm)
            return db_orm
        except IntegrityError as e:
            print(traceback.format_exc())
            self.db.rollback()
            if "no_login" in str(e):
                raise ValueError("Login já está em uso!")
            elif "no_email" in str(e):
                raise ValueError("Email já está em uso!")
            elif "nu_cpf" in str(e):
                raise ValueError("CPF já está em uso!")
            else:
                raise ValueError("Erro de integridade de dados")
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.post)

    async def put(self, usuario_id: int, orm: models.UsuarioPUT):
        """Atualiza um usuário"""
        try:
            # Criar dicionário apenas com campos não None
            update_data = {k: v for k, v in orm.dict().items() if v is not None}
            
            # Tratar email em lowercase
            if 'no_email' in update_data and update_data['no_email']:
                update_data['no_email'] = update_data['no_email'].lower()
            
            update_data['updated_at'] = datetime.now(timezone.utc).astimezone(AMSP)
            
            stmt = update(schemas.Usuarios).where(
                schemas.Usuarios.sq_usuario == usuario_id
            ).values(**update_data)
            
            self.db.execute(stmt)
            self.db.commit()
            
            return await self.get_by_id(usuario_id)
        except IntegrityError as e:
            self.db.rollback()
            if "no_email" in str(e):
                raise ValueError("Email já está em uso!")
            else:
                raise ValueError("Erro de integridade de dados")
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.put)

    async def delete(self, usuario_id: int):
        """Realiza exclusão lógica do usuário"""
        try:
            stmt = update(schemas.Usuarios).where(
                schemas.Usuarios.sq_usuario == usuario_id
            ).values(
                bo_status=False,
                deleted_at=datetime.now(timezone.utc).astimezone(AMSP)
            )
            self.db.execute(stmt)
            self.db.commit()
            return True
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.delete)

    # ---------------------- Autenticação ----------------------

    async def autenticar_usuario(self, login: str, senha: str) -> Tuple[bool, Optional[schemas.Usuarios], str]:
        """Autentica usuário com login e senha"""
        try:
            usuario = await self.get_by_login(login)
            
            if not usuario:
                return False, None, "Usuário não encontrado"
            
            if not usuario.bo_status:
                return False, None, "Usuário inativo"
            
            if not usuario.no_senha:
                return False, None, "Usuário sem senha definida"
            
            if not verificar_senha(senha, usuario.no_senha):
                return False, None, "Senha incorreta"
            
            return True, usuario, "Autenticação realizada com sucesso"
            
        except Exception as error:
            handle_error(error, self.autenticar_usuario)
            return False, None, "Erro interno do servidor"

    async def gerar_token_para_usuario(self, usuario: schemas.Usuarios) -> str:
        """Gera token JWT para o usuário"""
        try:
            payload = {
                "user_id": usuario.sq_usuario,
                "login": usuario.no_login,
                "competidor_id": usuario.competidor_id,
                "is_admin": usuario.competidor_id is None,
                "exp": datetime.utcnow() + timedelta(days=7)  # Token válido por 7 dias
            }
            
            return gerar_token_acesso(payload)
        except Exception as error:
            handle_error(error, self.gerar_token_para_usuario)

    async def alterar_senha(self, usuario_id: int, senha_atual: str, nova_senha: str) -> Tuple[bool, str]:
        """Altera a senha do usuário"""
        try:
            usuario = await self.get_by_id(usuario_id)
            
            if not usuario:
                return False, "Usuário não encontrado"
            
            if not verificar_senha(senha_atual, usuario.no_senha):
                return False, "Senha atual incorreta"
            
            # Gerar hash da nova senha
            nova_senha_hash = gerar_hash_senha(nova_senha)
            
            stmt = update(schemas.Usuarios).where(
                schemas.Usuarios.sq_usuario == usuario_id
            ).values(
                no_senha=nova_senha_hash,
                updated_at=datetime.now(timezone.utc).astimezone(AMSP)
            )
            
            self.db.execute(stmt)
            self.db.commit()
            
            return True, "Senha alterada com sucesso"
            
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.alterar_senha)
            return False, "Erro interno do servidor"

    # ---------------------- Cadastro Completo ----------------------

    async def cadastro_completo(self, dados: models.CadastroCompletoRequest) -> Tuple[bool, Dict[str, Any], str]:
        """Realiza cadastro completo: competidor + usuário"""
        try:
            # Iniciar transação
            self.db.begin()
            
            # 1. Verificar se login já existe
            usuario_existente = await self.get_by_login(dados.login)
            if usuario_existente:
                self.db.rollback()
                return False, {}, f'Login "{dados.login}" já está em uso!'
            
            # 2. Verificar se já existe competidor com mesmo nome e data nascimento
            competidor_existente = self.db.query(schemas.Competidores).filter(
                schemas.Competidores.nome == dados.nome,
                schemas.Competidores.data_nascimento == dados.data_nascimento
            ).first()
            
            if competidor_existente:
                self.db.rollback()
                return False, {}, 'Já existe um competidor com este nome e data de nascimento!'
            
            # 3. Criar competidor
            novo_competidor = schemas.Competidores(
                nome=dados.nome,
                login=dados.login,  # Login também no competidor para facilitar buscas
                data_nascimento=dados.data_nascimento,
                handicap=dados.handicap,
                cidade=dados.cidade,
                estado=dados.estado,
                sexo=dados.sexo,
                ativo=True,
                created_at=datetime.now(timezone.utc).astimezone(AMSP)
            )
            
            self.db.add(novo_competidor)
            self.db.flush()  # Para obter o ID sem fazer commit
            
            # 4. Criar usuário associado
            senha_hash = gerar_hash_senha(dados.senha)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            novo_usuario = schemas.Usuarios(
                nu_cpf=f"TEMP_{novo_competidor.id}_{timestamp}",  # CPF temporário único
                no_nome=dados.nome,
                no_login=dados.login.lower(),
                no_senha=senha_hash,
                no_email=None,  # Email opcional inicialmente
                competidor_id=novo_competidor.id,
                bo_status=True,
                created_at=datetime.now(timezone.utc).astimezone(AMSP)
            )
            
            self.db.add(novo_usuario)
            self.db.commit()
            
            # 5. Refresh dos objetos
            self.db.refresh(novo_competidor)
            self.db.refresh(novo_usuario)
            
            resultado = {
                'competidor': novo_competidor,
                'usuario': novo_usuario
            }
            
            return True, resultado, "Cadastro realizado com sucesso!"
            
        except IntegrityError as e:
            self.db.rollback()
            if "no_login" in str(e):
                return False, {}, "Login já está em uso!"
            else:
                return False, {}, "Erro de integridade de dados"
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.cadastro_completo)
            return False, {}, "Erro interno do servidor"

    # ---------------------- Recuperação de Senha ----------------------

    async def gerar_token_recuperacao(self, email: str) -> Tuple[bool, str, str]:
        """Gera token para recuperação de senha"""
        try:
            usuario = await self.get_by_email(email)
            
            if not usuario:
                return False, "", "Email não encontrado"
            
            if not usuario.bo_status:
                return False, "", "Usuário inativo"
            
            # Gerar token aleatório
            token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
            
            # TODO: Salvar token em tabela temporária com expiração
            # Por enquanto, retorna o token (implementar storage depois)
            
            return True, token, "Token gerado com sucesso"
            
        except Exception as error:
            handle_error(error, self.gerar_token_recuperacao)
            return False, "", "Erro interno do servidor"

    async def redefinir_senha_com_token(self, token: str, nova_senha: str) -> Tuple[bool, str]:
        """Redefine senha usando token de recuperação"""
        try:
            # TODO: Validar token na tabela temporária
            # Por enquanto, implementação básica
            
            # Gerar hash da nova senha
            nova_senha_hash = gerar_hash_senha(nova_senha)
            
            # TODO: Buscar usuário pelo token e atualizar senha
            
            return True, "Senha redefinida com sucesso"
            
        except Exception as error:
            handle_error(error, self.redefinir_senha_com_token)
            return False, "Erro interno do servidor"

    # ---------------------- Validações ----------------------

    async def login_disponivel(self, login: str, excluir_usuario_id: Optional[int] = None) -> bool:
        """Verifica se login está disponível"""
        try:
            query = self.db.query(schemas.Usuarios).filter(
                schemas.Usuarios.no_login == login.lower()
            )
            
            if excluir_usuario_id:
                query = query.filter(schemas.Usuarios.sq_usuario != excluir_usuario_id)
            
            usuario = query.first()
            return usuario is None
            
        except Exception as error:
            handle_error(error, self.login_disponivel)
            return False

    async def email_disponivel(self, email: str, excluir_usuario_id: Optional[int] = None) -> bool:
        """Verifica se email está disponível"""
        try:
            query = self.db.query(schemas.Usuarios).filter(
                schemas.Usuarios.no_email == email.lower()
            )
            
            if excluir_usuario_id:
                query = query.filter(schemas.Usuarios.sq_usuario != excluir_usuario_id)
            
            usuario = query.first()
            return usuario is None
            
        except Exception as error:
            handle_error(error, self.email_disponivel)
            return False

    # ---------------------- Estatísticas ----------------------

    async def get_estatisticas_usuarios(self):
        """Recupera estatísticas dos usuários"""
        try:
            total_usuarios = self.db.query(schemas.Usuarios).filter(
                schemas.Usuarios.bo_status == True
            ).count()
            
            usuarios_admin = self.db.query(schemas.Usuarios).filter(
                schemas.Usuarios.bo_status == True,
                schemas.Usuarios.competidor_id.is_(None)
            ).count()
            
            usuarios_competidores = self.db.query(schemas.Usuarios).filter(
                schemas.Usuarios.bo_status == True,
                schemas.Usuarios.competidor_id.isnot(None)
            ).count()
            
            usuarios_com_email = self.db.query(schemas.Usuarios).filter(
                schemas.Usuarios.bo_status == True,
                schemas.Usuarios.no_email.isnot(None)
            ).count()
            
            return {
                'total_usuarios': total_usuarios,
                'usuarios_admin': usuarios_admin,
                'usuarios_competidores': usuarios_competidores,
                'usuarios_com_email': usuarios_com_email,
                'percentual_com_email': round((usuarios_com_email / total_usuarios * 100), 2) if total_usuarios > 0 else 0
            }
            
        except Exception as error:
            handle_error(error, self.get_estatisticas_usuarios)

    # ---------------------- Operações em Lote ----------------------

    async def criar_multiplos_usuarios(self, usuarios: List[models.UsuarioPOST]):
        """Cria múltiplos usuários em uma transação"""
        try:
            usuarios_criados = []
            erros_validacao = []
            
            # Validar todos os usuários antes de criar
            for i, usuario_data in enumerate(usuarios):
                # Verificar se login já existe
                if not await self.login_disponivel(usuario_data.no_login):
                    erros_validacao.append({
                        'index': i,
                        'erro': f'Login "{usuario_data.no_login}" já está em uso',
                        'campo': 'no_login'
                    })
                
                # Verificar se email já existe (se fornecido)
                if usuario_data.no_email and not await self.email_disponivel(usuario_data.no_email):
                    erros_validacao.append({
                        'index': i,
                        'erro': f'Email "{usuario_data.no_email}" já está em uso',
                        'campo': 'no_email'
                    })
            
            if erros_validacao:
                raise ValueError(f"Erros de validação encontrados: {erros_validacao}")
            
            # Criar usuários
            for usuario_data in usuarios:
                senha_hash = gerar_hash_senha(usuario_data.no_senha)
                
                db_orm = schemas.Usuarios(
                    nu_cpf=usuario_data.nu_cpf,
                    no_nome=usuario_data.no_nome,
                    no_login=usuario_data.no_login.lower(),
                    no_senha=senha_hash,
                    no_email=usuario_data.no_email.lower() if usuario_data.no_email else None,
                    no_foto=usuario_data.no_foto,
                    competidor_id=usuario_data.competidor_id,
                    bo_status=True,
                    created_at=datetime.now(timezone.utc).astimezone(AMSP)
                )
                
                self.db.add(db_orm)
                usuarios_criados.append(db_orm)
            
            self.db.commit()
            
            # Refresh todos os objetos
            for usuario in usuarios_criados:
                self.db.refresh(usuario)
            
            return usuarios_criados
            
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.criar_multiplos_usuarios)

    async def atualizar_multiplos_usuarios(self, updates: List[Dict[str, Any]]):
        """Atualiza múltiplos usuários em uma transação"""
        try:
            # updates = [{'id': 1, 'no_nome': 'Novo Nome', 'no_email': 'novo@email.com'}]
            for update in updates:
                usuario_id = update.pop('id')  # Remove ID do update
                
                # Tratar email em lowercase
                if 'no_email' in update and update['no_email']:
                    update['no_email'] = update['no_email'].lower()
                
                update['updated_at'] = datetime.now(timezone.utc).astimezone(AMSP)
                
                stmt = update(schemas.Usuarios).where(
                    schemas.Usuarios.sq_usuario == usuario_id
                ).values(**update)
                
                self.db.execute(stmt)
            
            self.db.commit()
            return True
            
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.atualizar_multiplos_usuarios)

    # ---------------------- Relatórios ----------------------

    async def relatorio_usuarios_ativos_inativos(self):
        """Gera relatório de usuários ativos e inativos"""
        try:
            relatorio = self.db.query(
                schemas.Usuarios.bo_status.label('status'),
                func.count(schemas.Usuarios.sq_usuario).label('total'),
                func.count(
                    func.nullif(schemas.Usuarios.competidor_id, None)
                ).label('competidores'),
                func.count(
                    func.nullif(schemas.Usuarios.no_email, None)
                ).label('com_email')
            ).group_by(
                schemas.Usuarios.bo_status
            ).all()

            return relatorio
            
        except Exception as error:
            handle_error(error, self.relatorio_usuarios_ativos_inativos)

    # ---------------------- Logs de Acesso ----------------------

    async def registrar_login(self, usuario_id: int, ip_address: str = None, user_agent: str = None):
        """Registra log de login do usuário"""
        try:
            # TODO: Implementar tabela de logs de acesso
            # Por enquanto, apenas atualizar last_login no usuário
            
            stmt = update(schemas.Usuarios).where(
                schemas.Usuarios.sq_usuario == usuario_id
            ).values(
                updated_at=datetime.now(timezone.utc).astimezone(AMSP)
            )
            
            self.db.execute(stmt)
            self.db.commit()
            
            return True
            
        except Exception as error:
            handle_error(error, self.registrar_login)

    async def get_historico_acessos(self, usuario_id: int, limite: int = 10):
        """Recupera histórico de acessos do usuário"""
        try:
            # TODO: Implementar quando tivermos tabela de logs
            # Por enquanto retorna informações básicas
            
            usuario = await self.get_by_id(usuario_id)
            if usuario:
                return [{
                    'data_acesso': usuario.updated_at or usuario.created_at,
                    'tipo': 'login',
                    'ip_address': 'N/A',
                    'user_agent': 'N/A'
                }]
            
            return []
            
        except Exception as error:
            handle_error(error, self.get_historico_acessos)

    # ---------------------- Busca e Filtros Avançados ----------------------

    async def buscar_usuarios_avancado(self, filtros: Dict[str, Any]):
        """Busca avançada de usuários com múltiplos filtros"""
        try:
            query = self.db.query(schemas.Usuarios).options(
                joinedload(schemas.Usuarios.competidor)
            )

            # Filtro por nome (busca em nome do usuário e do competidor)
            if filtros.get('busca_geral'):
                busca = f"%{filtros['busca_geral']}%"
                query = query.filter(
                    or_(
                        schemas.Usuarios.no_nome.ilike(busca),
                        schemas.Usuarios.no_login.ilike(busca),
                        schemas.Usuarios.no_email.ilike(busca)
                    )
                )

            # Filtro por data de criação
            if filtros.get('data_inicio'):
                query = query.filter(
                    func.date(schemas.Usuarios.created_at) >= filtros['data_inicio']
                )
            
            if filtros.get('data_fim'):
                query = query.filter(
                    func.date(schemas.Usuarios.created_at) <= filtros['data_fim']
                )

            # Filtro por tipo de usuário
            if filtros.get('tipo_usuario') == 'admin':
                query = query.filter(schemas.Usuarios.competidor_id.is_(None))
            elif filtros.get('tipo_usuario') == 'competidor':
                query = query.filter(schemas.Usuarios.competidor_id.isnot(None))

            # Filtro por status
            if filtros.get('status') is not None:
                query = query.filter(schemas.Usuarios.bo_status == filtros['status'])

            # Filtro por presença de email
            if filtros.get('tem_email') is not None:
                if filtros['tem_email']:
                    query = query.filter(schemas.Usuarios.no_email.isnot(None))
                else:
                    query = query.filter(schemas.Usuarios.no_email.is_(None))

            # Ordenação
            ordem = filtros.get('ordenar_por', 'nome')
            direcao = filtros.get('direcao', 'asc')
            
            if ordem == 'nome':
                if direcao == 'desc':
                    query = query.order_by(schemas.Usuarios.no_nome.desc())
                else:
                    query = query.order_by(schemas.Usuarios.no_nome.asc())
            elif ordem == 'login':
                if direcao == 'desc':
                    query = query.order_by(schemas.Usuarios.no_login.desc())
                else:
                    query = query.order_by(schemas.Usuarios.no_login.asc())
            elif ordem == 'data_criacao':
                if direcao == 'desc':
                    query = query.order_by(schemas.Usuarios.created_at.desc())
                else:
                    query = query.order_by(schemas.Usuarios.created_at.asc())

            # Paginação
            if filtros.get('pagina') and filtros.get('tamanho_pagina'):
                pagina = filtros['pagina']
                tamanho = filtros['tamanho_pagina']
                query = query.limit(tamanho).offset((pagina - 1) * tamanho)

            return query.all()
            
        except Exception as error:
            handle_error(error, self.buscar_usuarios_avancado)

    # ---------------------- Validação de Dados ----------------------

    async def validar_dados_usuario(self, dados: Dict[str, Any], excluir_usuario_id: Optional[int] = None):
        """Valida dados do usuário antes de criar/atualizar"""
        try:
            erros = []

            # Validar login
            if 'no_login' in dados:
                if not await self.login_disponivel(dados['no_login'], excluir_usuario_id):
                    erros.append({
                        'campo': 'no_login',
                        'erro': f'Login "{dados["no_login"]}" já está em uso'
                    })

            # Validar email
            if 'no_email' in dados and dados['no_email']:
                if not await self.email_disponivel(dados['no_email'], excluir_usuario_id):
                    erros.append({
                        'campo': 'no_email',
                        'erro': f'Email "{dados["no_email"]}" já está em uso'
                    })

            # Validar CPF (básico)
            if 'nu_cpf' in dados:
                cpf = dados['nu_cpf']
                if len(cpf) != 11 or not cpf.isdigit():
                    if not cpf.startswith('TEMP_'):  # Permitir CPFs temporários
                        erros.append({
                            'campo': 'nu_cpf',
                            'erro': 'CPF deve ter 11 dígitos numéricos'
                        })

            # Validar associação com competidor
            if 'competidor_id' in dados and dados['competidor_id']:
                competidor = self.db.query(schemas.Competidores).filter(
                    schemas.Competidores.id == dados['competidor_id'],
                    schemas.Competidores.ativo == True
                ).first()
                
                if not competidor:
                    erros.append({
                        'campo': 'competidor_id',
                        'erro': 'Competidor não encontrado ou inativo'
                    })
                else:
                    # Verificar se competidor já tem usuário
                    usuario_existente = self.db.query(schemas.Usuarios).filter(
                        schemas.Usuarios.competidor_id == dados['competidor_id'],
                        schemas.Usuarios.bo_status == True
                    )
                    
                    if excluir_usuario_id:
                        usuario_existente = usuario_existente.filter(
                            schemas.Usuarios.sq_usuario != excluir_usuario_id
                        )
                    
                    if usuario_existente.first():
                        erros.append({
                            'campo': 'competidor_id',
                            'erro': 'Competidor já possui usuário associado'
                        })

            return erros
            
        except Exception as error:
            handle_error(error, self.validar_dados_usuario)
            return [{'campo': 'geral', 'erro': 'Erro interno na validação'}]

    # ---------------------- Operações de Administração ----------------------

    async def promover_para_admin(self, usuario_id: int):
        """Promove usuário para administrador (remove associação com competidor)"""
        try:
            stmt = update(schemas.Usuarios).where(
                schemas.Usuarios.sq_usuario == usuario_id
            ).values(
                competidor_id=None,
                updated_at=datetime.now(timezone.utc).astimezone(AMSP)
            )
            
            self.db.execute(stmt)
            self.db.commit()
            
            return await self.get_by_id(usuario_id)
            
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.promover_para_admin)

    async def associar_competidor(self, usuario_id: int, competidor_id: int):
        """Associa usuário a um competidor"""
        try:
            # Verificar se competidor existe e está ativo
            competidor = self.db.query(schemas.Competidores).filter(
                schemas.Competidores.id == competidor_id,
                schemas.Competidores.ativo == True
            ).first()
            
            if not competidor:
                raise ValueError("Competidor não encontrado ou inativo")
            
            # Verificar se competidor já tem usuário
            usuario_existente = self.db.query(schemas.Usuarios).filter(
                schemas.Usuarios.competidor_id == competidor_id,
                schemas.Usuarios.bo_status == True,
                schemas.Usuarios.sq_usuario != usuario_id
            ).first()
            
            if usuario_existente:
                raise ValueError("Competidor já possui usuário associado")
            
            stmt = update(schemas.Usuarios).where(
                schemas.Usuarios.sq_usuario == usuario_id
            ).values(
                competidor_id=competidor_id,
                updated_at=datetime.now(timezone.utc).astimezone(AMSP)
            )
            
            self.db.execute(stmt)
            self.db.commit()
            
            return await self.get_by_id(usuario_id)
            
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.associar_competidor)

    async def resetar_senha(self, usuario_id: int, nova_senha: str):
        """Reseta senha do usuário (função administrativa)"""
        try:
            nova_senha_hash = gerar_hash_senha(nova_senha)
            
            stmt = update(schemas.Usuarios).where(
                schemas.Usuarios.sq_usuario == usuario_id
            ).values(
                no_senha=nova_senha_hash,
                updated_at=datetime.now(timezone.utc).astimezone(AMSP)
            )
            
            self.db.execute(stmt)
            self.db.commit()
            
            return True
            
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.resetar_senha)