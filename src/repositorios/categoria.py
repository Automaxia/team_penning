from sqlalchemy import select, delete, update, func, desc, asc, and_, or_
from sqlalchemy.orm import Session, joinedload
from src.database import models, schemas
from src.utils.error_handler import handle_error
from src.utils.utils_lctp import UtilsLCTP
from src.utils.config_lctp import ConfigLCTP
from src.utils.exceptions_lctp import CategoriaException
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
import pytz

AMSP = pytz.timezone('America/Sao_Paulo')

class RepositorioCategoria:
    """Repositório para operações com categorias do sistema LCTP"""
    
    def __init__(self, db: Session):
        self.db = db

    # ---------------------- Operações Básicas ----------------------

    async def get_all(self, ativas_apenas: bool = True) -> List[schemas.Categorias]:
        """Recupera todas as categorias"""
        try:
            stmt = select(schemas.Categorias)
            
            if ativas_apenas:
                stmt = stmt.where(schemas.Categorias.ativa == True)
            
            stmt = stmt.order_by(schemas.Categorias.nome)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_all)

    async def get_by_id(self, categoria_id: int) -> Optional[schemas.Categorias]:
        """Recupera uma categoria pelo ID"""
        try:
            stmt = select(schemas.Categorias).where(
                schemas.Categorias.id == categoria_id
            )
            
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self.get_by_id)

    async def get_by_nome(self, nome: str) -> Optional[schemas.Categorias]:
        """Recupera uma categoria pelo nome"""
        try:
            stmt = select(schemas.Categorias).where(
                schemas.Categorias.nome.ilike(f"%{nome}%")
            )
            
            return self.db.execute(stmt).scalars().first()
        except Exception as error:
            handle_error(error, self.get_by_nome)

    async def get_by_tipo(self, tipo: schemas.TipoCategoria, ativas_apenas: bool = True) -> List[schemas.Categorias]:
        """Recupera categorias por tipo"""
        try:
            stmt = select(schemas.Categorias).where(
                schemas.Categorias.tipo == tipo
            )
            
            if ativas_apenas:
                stmt = stmt.where(schemas.Categorias.ativa == True)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_by_tipo)

    async def post(self, categoria_data: models.CategoriaPOST) -> schemas.Categorias:
        """Cria uma nova categoria"""
        try:
            # Verificar se já existe categoria com o mesmo nome
            categoria_existente = await self.get_by_nome(categoria_data.nome)
            if categoria_existente:
                raise CategoriaException(f"Já existe uma categoria com o nome '{categoria_data.nome}'")

            # Validar regras específicas por tipo
            await self._validar_regras_categoria(categoria_data)

            db_categoria = schemas.Categorias(
                nome=categoria_data.nome,
                tipo=categoria_data.tipo,
                descricao=categoria_data.descricao,
                handicap_max_trio=categoria_data.handicap_max_trio,
                idade_max_trio=categoria_data.idade_max_trio,
                idade_min_individual=categoria_data.idade_min_individual,
                idade_max_individual=categoria_data.idade_max_individual,
                permite_sorteio=categoria_data.permite_sorteio,
                min_inscricoes_sorteio=categoria_data.min_inscricoes_sorteio,
                max_inscricoes_sorteio=categoria_data.max_inscricoes_sorteio,
                sorteio_completo=categoria_data.sorteio_completo,
                tipo_pontuacao=categoria_data.tipo_pontuacao,
                ativa=categoria_data.ativa
            )

            self.db.add(db_categoria)
            self.db.commit()
            self.db.refresh(db_categoria)
            
            return db_categoria
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.post)

    async def put(self, categoria_id: int, categoria_data: models.CategoriaPUT) -> Optional[schemas.Categorias]:
        """Atualiza uma categoria"""
        try:
            categoria_existente = await self.get_by_id(categoria_id)
            if not categoria_existente:
                raise CategoriaException(f"Categoria com ID {categoria_id} não encontrada")

            # Verificar nome duplicado (se alterado)
            if categoria_data.nome and categoria_data.nome != categoria_existente.nome:
                categoria_nome_existente = await self.get_by_nome(categoria_data.nome)
                if categoria_nome_existente and categoria_nome_existente.id != categoria_id:
                    raise CategoriaException(f"Já existe uma categoria com o nome '{categoria_data.nome}'")

            # Criar dicionário apenas com campos não None
            update_data = {k: v for k, v in categoria_data.model_dump().items() if v is not None}
            
            if update_data:
                # Validar regras se necessário
                if any(key in update_data for key in ['tipo', 'handicap_max_trio', 'idade_max_trio']):
                    categoria_temp = models.CategoriaPOST(
                        nome=update_data.get('nome', categoria_existente.nome),
                        tipo=update_data.get('tipo', categoria_existente.tipo),
                        descricao=update_data.get('descricao', categoria_existente.descricao),
                        handicap_max_trio=update_data.get('handicap_max_trio', categoria_existente.handicap_max_trio),
                        idade_max_trio=update_data.get('idade_max_trio', categoria_existente.idade_max_trio),
                        idade_min_individual=update_data.get('idade_min_individual', categoria_existente.idade_min_individual),
                        idade_max_individual=update_data.get('idade_max_individual', categoria_existente.idade_max_individual),
                        permite_sorteio=update_data.get('permite_sorteio', categoria_existente.permite_sorteio),
                        min_inscricoes_sorteio=update_data.get('min_inscricoes_sorteio', categoria_existente.min_inscricoes_sorteio),
                        max_inscricoes_sorteio=update_data.get('max_inscricoes_sorteio', categoria_existente.max_inscricoes_sorteio),
                        sorteio_completo=update_data.get('sorteio_completo', categoria_existente.sorteio_completo),
                        tipo_pontuacao=update_data.get('tipo_pontuacao', categoria_existente.tipo_pontuacao),
                        ativa=update_data.get('ativa', categoria_existente.ativa)
                    )
                    await self._validar_regras_categoria(categoria_temp)

                stmt = update(schemas.Categorias).where(
                    schemas.Categorias.id == categoria_id
                ).values(**update_data)
                
                self.db.execute(stmt)
                self.db.commit()
            
            return await self.get_by_id(categoria_id)
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.put)

    async def delete(self, categoria_id: int) -> bool:
        """Remove uma categoria (soft delete)"""
        try:
            categoria = await self.get_by_id(categoria_id)
            if not categoria:
                raise CategoriaException(f"Categoria com ID {categoria_id} não encontrada")

            # Verificar se a categoria tem trios associados
            trios_count = self.db.execute(
                select(func.count(schemas.Trios.id)).where(
                    schemas.Trios.categoria_id == categoria_id
                )
            ).scalar()

            if trios_count > 0:
                # Soft delete - apenas marcar como inativa
                stmt = update(schemas.Categorias).where(
                    schemas.Categorias.id == categoria_id
                ).values(ativa=False)
                
                self.db.execute(stmt)
                self.db.commit()
                return True
            else:
                # Delete físico se não tem trios
                stmt = delete(schemas.Categorias).where(
                    schemas.Categorias.id == categoria_id
                )
                
                self.db.execute(stmt)
                self.db.commit()
                return True
                
        except Exception as error:
            self.db.rollback()
            handle_error(error, self.delete)

    # ---------------------- Consultas Especializadas ----------------------

    async def get_categorias_competidor(self, competidor_id: int) -> List[schemas.Categorias]:
        """Retorna categorias nas quais um competidor pode participar"""
        try:
            # Buscar dados do competidor
            competidor = self.db.execute(
                select(schemas.Competidores).where(
                    schemas.Competidores.id == competidor_id
                )
            ).scalars().first()

            if not competidor:
                return []

            categorias_possiveis = []
            todas_categorias = await self.get_all()

            for categoria in todas_categorias:
                pode_participar = await self._competidor_pode_participar(competidor, categoria)
                if pode_participar:
                    categorias_possiveis.append(categoria)

            return categorias_possiveis
        except Exception as error:
            handle_error(error, self.get_categorias_competidor)

    async def get_categorias_que_permitem_sorteio(self) -> List[schemas.Categorias]:
        """Retorna categorias que permitem sorteio"""
        try:
            stmt = select(schemas.Categorias).where(
                schemas.Categorias.permite_sorteio == True,
                schemas.Categorias.ativa == True
            ).order_by(schemas.Categorias.nome)
            
            return self.db.execute(stmt).scalars().all()
        except Exception as error:
            handle_error(error, self.get_categorias_que_permitem_sorteio)

    async def get_estatisticas_categoria(self, categoria_id: int, ano: Optional[int] = None) -> Dict[str, Any]:
        """Gera estatísticas de uma categoria"""
        try:
            categoria = await self.get_by_id(categoria_id)
            if not categoria:
                return {}

            # Query base para trios da categoria
            query = self.db.query(schemas.Trios).filter(
                schemas.Trios.categoria_id == categoria_id
            )

            if ano:
                query = query.join(schemas.Provas).filter(
                    func.extract('year', schemas.Provas.data) == ano
                )

            trios = query.all()

            # Estatísticas básicas
            total_trios = len(trios)
            total_competidores = total_trios * 3

            # Trios por tipo de formação
            manuais = len([t for t in trios if t.formacao_manual])
            sorteados = total_trios - manuais

            # Análise de handicap
            handicaps = [t.handicap_total for t in trios if t.handicap_total]
            handicap_medio = sum(handicaps) / len(handicaps) if handicaps else 0

            # Análise de idade
            idades = [t.idade_total for t in trios if t.idade_total]
            idade_media = sum(idades) / len(idades) if idades else 0

            return {
                'categoria': categoria,
                'ano': ano,
                'total_trios': total_trios,
                'total_competidores': total_competidores,
                'formacao': {
                    'manual': manuais,
                    'sorteio': sorteados
                },
                'handicap': {
                    'medio': round(handicap_medio, 2),
                    'minimo': min(handicaps) if handicaps else 0,
                    'maximo': max(handicaps) if handicaps else 0
                },
                'idade': {
                    'media': round(idade_media, 1),
                    'minima': min(idades) if idades else 0,
                    'maxima': max(idades) if idades else 0
                }
            }
        except Exception as error:
            handle_error(error, self.get_estatisticas_categoria)

    async def get_categorias_por_prova(self, prova_id: int) -> List[Dict[str, Any]]:
        """Retorna categorias de uma prova com estatísticas"""
        try:
            # Buscar categorias que têm trios na prova
            stmt = select(
                schemas.Categorias,
                func.count(schemas.Trios.id).label('total_trios')
            ).join(
                schemas.Trios
            ).where(
                schemas.Trios.prova_id == prova_id
            ).group_by(
                schemas.Categorias.id
            ).order_by(
                schemas.Categorias.nome
            )

            resultados = self.db.execute(stmt).all()
            
            categorias_prova = []
            for categoria, total_trios in resultados:
                categorias_prova.append({
                    'categoria': categoria,
                    'total_trios': total_trios,
                    'total_competidores': total_trios * 3
                })

            return categorias_prova
        except Exception as error:
            handle_error(error, self.get_categorias_por_prova)

    # ---------------------- Validações ----------------------

    async def _validar_regras_categoria(self, categoria_data: models.CategoriaPOST):
        """Valida regras específicas por tipo de categoria"""
        try:
            regras = ConfigLCTP.REGRAS_CATEGORIAS.get(categoria_data.tipo.value, {})
            
            # Validações por tipo
            match categoria_data.tipo:
                case schemas.TipoCategoria.BABY:
                    if not categoria_data.sorteio_completo:
                        raise CategoriaException("Categoria Baby deve ter sorteio completo")
                    if categoria_data.idade_max_individual is None:
                        categoria_data.idade_max_individual = regras.get('idade_max', 12)
                
                case schemas.TipoCategoria.KIDS:
                    if categoria_data.idade_min_individual is None:
                        categoria_data.idade_min_individual = regras.get('idade_min', 13)
                    if categoria_data.idade_max_individual is None:
                        categoria_data.idade_max_individual = regras.get('idade_max', 17)
                    if categoria_data.permite_sorteio and not categoria_data.max_inscricoes_sorteio:
                        categoria_data.max_inscricoes_sorteio = regras.get('max_sorteio', 9)
                
                case schemas.TipoCategoria.MIRIM:
                    if categoria_data.idade_max_trio is None:
                        categoria_data.idade_max_trio = regras.get('idade_max_trio', 36)
                
                case schemas.TipoCategoria.FEMININA:
                    if categoria_data.permite_sorteio and not categoria_data.max_inscricoes_sorteio:
                        categoria_data.max_inscricoes_sorteio = regras.get('max_sorteio', 9)
                
                case schemas.TipoCategoria.HANDICAP:
                    if categoria_data.handicap_max_trio is None:
                        categoria_data.handicap_max_trio = regras.get('handicap_max_trio', 11)

            # Validar limites de sorteio
            if categoria_data.permite_sorteio:
                if categoria_data.min_inscricoes_sorteio > categoria_data.max_inscricoes_sorteio:
                    raise CategoriaException("Mínimo de inscrições não pode ser maior que o máximo")
                
                if categoria_data.min_inscricoes_sorteio < 3:
                    raise CategoriaException("Mínimo de inscrições deve ser pelo menos 3")

        except Exception as error:
            handle_error(error, self._validar_regras_categoria)

    async def _competidor_pode_participar(self, competidor: schemas.Competidores, categoria: schemas.Categorias) -> bool:
        """Verifica se um competidor pode participar de uma categoria"""
        try:
            idade = competidor.idade

            # Verificar idade mínima
            if categoria.idade_min_individual and idade < categoria.idade_min_individual:
                return False

            # Verificar idade máxima
            if categoria.idade_max_individual and idade > categoria.idade_max_individual:
                return False

            # Verificar sexo para categoria feminina
            if categoria.tipo == schemas.TipoCategoria.FEMININA and competidor.sexo != 'F':
                return False

            # Categoria aberta aceita todos
            if categoria.tipo == schemas.TipoCategoria.ABERTA:
                return True

            return True
        except Exception as error:
            handle_error(error, self._competidor_pode_participar)

    async def validar_trio_categoria(self, competidores_ids: List[int], categoria_id: int) -> Tuple[bool, str]:
        """Valida se um trio pode participar de uma categoria"""
        try:
            if len(competidores_ids) != 3:
                return False, "Um trio deve ter exatamente 3 competidores"

            categoria = await self.get_by_id(categoria_id)
            if not categoria:
                return False, "Categoria não encontrada"

            # Buscar competidores
            competidores = self.db.execute(
                select(schemas.Competidores).where(
                    schemas.Competidores.id.in_(competidores_ids)
                )
            ).scalars().all()

            if len(competidores) != 3:
                return False, "Nem todos os competidores foram encontrados"

            # Validar categoria feminina
            if categoria.tipo == schemas.TipoCategoria.FEMININA:
                if not all(c.sexo == 'F' for c in competidores):
                    return False, "Categoria feminina aceita apenas mulheres"

            # Validar limite de handicap
            if categoria.handicap_max_trio:
                handicap_total = sum(c.handicap for c in competidores)
                if handicap_total > categoria.handicap_max_trio:
                    return False, f"Handicap total ({handicap_total}) excede o limite ({categoria.handicap_max_trio})"

            # Validar limite de idade
            if categoria.idade_max_trio:
                idade_total = sum(c.idade for c in competidores if c.idade)
                if idade_total > categoria.idade_max_trio:
                    return False, f"Idade total ({idade_total}) excede o limite ({categoria.idade_max_trio})"

            # Validar idades individuais
            for competidor in competidores:
                if not await self._competidor_pode_participar(competidor, categoria):
                    return False, f"Competidor {competidor.nome} não atende aos critérios da categoria"

            return True, "Trio válido para a categoria"
        except Exception as error:
            handle_error(error, self.validar_trio_categoria)

    # ---------------------- Relatórios ----------------------

    async def gerar_relatorio_participacao(self, ano: Optional[int] = None) -> Dict[str, Any]:
        """Gera relatório de participação por categoria"""
        try:
            categorias = await self.get_all()
            relatorio = {}

            for categoria in categorias:
                estatisticas = await self.get_estatisticas_categoria(categoria.id, ano)
                relatorio[categoria.nome] = estatisticas

            return {
                'ano': ano or 'todos',
                'total_categorias': len(categorias),
                'categorias': relatorio,
                'gerado_em': datetime.now(timezone.utc).astimezone(AMSP)
            }
        except Exception as error:
            handle_error(error, self.gerar_relatorio_participacao)

    async def exportar_configuracao_categorias(self) -> List[Dict[str, Any]]:
        """Exporta configuração de todas as categorias"""
        try:
            categorias = await self.get_all(ativas_apenas=False)
            
            export_data = []
            for categoria in categorias:
                categoria_dict = {
                    'id': categoria.id,
                    'nome': categoria.nome,
                    'tipo': categoria.tipo.value,
                    'descricao': categoria.descricao,
                    'handicap_max_trio': categoria.handicap_max_trio,
                    'idade_max_trio': categoria.idade_max_trio,
                    'idade_min_individual': categoria.idade_min_individual,
                    'idade_max_individual': categoria.idade_max_individual,
                    'permite_sorteio': categoria.permite_sorteio,
                    'min_inscricoes_sorteio': categoria.min_inscricoes_sorteio,
                    'max_inscricoes_sorteio': categoria.max_inscricoes_sorteio,
                    'sorteio_completo': categoria.sorteio_completo,
                    'tipo_pontuacao': categoria.tipo_pontuacao,
                    'ativa': categoria.ativa
                }
                export_data.append(categoria_dict)
            
            return export_data
        except Exception as error:
            handle_error(error, self.exportar_configuracao_categorias)