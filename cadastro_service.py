from datetime import datetime, timedelta
from api.client import FirebaseClient
from services.pg_db import PostgresDatabase


class CadastroService:
    def __init__(self):
        self.client = FirebaseClient()
        self.db = None

        self.firebase_ok = False
        self.db_ok = False

        self.erro_firebase = None
        self.erro_db = None

        self.cadastros_pendentes = []
        self.cadastros_realizados = []

        # cache temporário para evitar que uma leitura atrasada do Firebase
        # faça a ficha recém-concluída voltar para pendente
        self._conclusoes_recentes = {}
        self._janela_protecao_conclusao = timedelta(minutes=3)

    # ------------------------------------------------------------------
    # INICIALIZAÇÃO
    # ------------------------------------------------------------------
    def inicializar_firebase(self):
        if self.firebase_ok:
            return True

        try:
            autenticado = self.client.autenticar(
                "paulo_matos@tegporto.com.br",
                "qwerty12"
            )

            if not autenticado:
                raise RuntimeError("Falha na autenticação com o Firebase.")

            self.firebase_ok = True
            self.erro_firebase = None
            return True

        except Exception as e:
            self.firebase_ok = False
            self.erro_firebase = str(e)
            return False

    def inicializar_db(self):
        if self.db_ok and self.db is not None:
            return True

        try:
            self.db = PostgresDatabase()
            self.db_ok = True
            self.erro_db = None
            return True

        except Exception as e:
            self.db = None
            self.db_ok = False
            self.erro_db = repr(e)
            return False

    # ------------------------------------------------------------------
    # ATUALIZAÇÃO GERAL
    # ------------------------------------------------------------------
    def atualizar_fichas_api(self, visitantes=None):
        if not self.firebase_ok:
            raise RuntimeError(
                self.erro_firebase or
                "Firebase ainda não inicializado."
            )

        if visitantes is None:
            visitantes, _ = self.client.buscar_visitantes()

        self._limpar_conclusoes_recentes_expiradas()

        novos_pendentes = []
        novos_realizados = []

        ids_anteriores = {
            (c.get("origem"), c.get("id"))
            for c in self.cadastros_pendentes
        }

        novos_cadastros = []

        for registro in visitantes:
            origem = registro.get("origem", "visitantes")

            if origem == "consumos":
                cadastro = self.converter_consumo_para_cadastro(registro)
            else:
                cadastro = self.converter_visitante_para_cadastro(registro)

            registro_id = cadastro.get("id")
            if not registro_id:
                continue

            chave_origem = cadastro.get("origem", origem)

            conclusao_local = None
            if self.db_ok and self.db is not None:
                try:
                    conclusao_local = self.db.obter_conclusao_local(chave_origem, registro_id)
                except Exception:
                    conclusao_local = None

            em_janela_protecao = self._registro_em_janela_de_conclusao(chave_origem, registro_id)

            # preserva realizado local apenas se o cadastro não foi claramente reaberto
            if (em_janela_protecao or conclusao_local) and cadastro.get("status") != "pendente":
                cadastro["status"] = "realizado"
                cadastro["concluido_em"] = (
                    cadastro.get("concluido_em")
                    or conclusao_local
                    or datetime.now().isoformat()
                )

                if not cadastro.get("smartcard"):
                    cadastro["smartcard"] = registro.get("smartcard", "") or cadastro.get("smartcard", "")

                cadastro["status_balgate"] = "realizado"
                cadastro["concluido_no_sistema"] = True

            status = cadastro.get("status", "pendente")

            concluido_em_local = None
            if status == "realizado":
                concluido_em_local = (
                    cadastro.get("concluido_em")
                    or conclusao_local
                    or datetime.now().isoformat()
                )

            if self.db_ok and self.db is not None:
                try:
                    self.db.upsert_ficha(
                        origem=chave_origem,
                        registro_id=registro_id,
                        status=status,
                        concluido_em_local=concluido_em_local,
                    )
                except Exception:
                    pass

            if status == "realizado":
                cadastro["concluido_em"] = (
                    cadastro.get("concluido_em")
                    or conclusao_local
                )

                # evita nova ida ao banco só para checar expiração
                concluido_ref = self._parse_datetime_generico(cadastro.get("concluido_em"))
                if concluido_ref:
                    limite = datetime.now() - timedelta(hours=24)
                    if concluido_ref <= limite:
                        continue

                novos_realizados.append(cadastro)
            else:
                novos_pendentes.append(cadastro)

                chave = (cadastro.get("origem"), cadastro.get("id"))
                if chave not in ids_anteriores:
                    novos_cadastros.append(cadastro)

        # pendentes mais recentes primeiro
        novos_pendentes.sort(
            key=lambda c: self._parse_datetime_generico(c.get("datahora_evento")) or datetime.min,
            reverse=True,
        )

        # realizados mais recentes primeiro
        novos_realizados.sort(
            key=lambda c: self._parse_datetime_generico(c.get("concluido_em")) or datetime.min,
            reverse=True,
        )

        self.cadastros_pendentes = novos_pendentes
        self.cadastros_realizados = novos_realizados

        if self.db_ok and self.db is not None:
            try:
                self.db.remover_expiradas(horas=24)
            except Exception:
                pass

        return novos_cadastros

    # ------------------------------------------------------------------
    # FILTRO
    # ------------------------------------------------------------------
    def filtrar(self, termo):
        termo = (termo or "").strip().lower()

        if not termo:
            return self.cadastros_pendentes, self.cadastros_realizados

        def match(c):
            return (
                termo in str(c.get("placa", "")).lower()
                or termo in str(c.get("motorista_nome", "")).lower()
                or termo in str(c.get("empresa_motorista", "")).lower()
            )

        return (
            [c for c in self.cadastros_pendentes if match(c)],
            [c for c in self.cadastros_realizados if match(c)],
        )

    # ------------------------------------------------------------------
    # AUXILIARES
    # ------------------------------------------------------------------
    def _pick(self, origem, *keys, default=""):
        for k in keys:
            if origem.get(k) not in (None, "", [], {}):
                valor = origem.get(k)
                return valor.upper() if isinstance(valor, str) else valor
        return default.upper() if isinstance(default, str) else default

    def _normalizar_status(self, status_raw):
        status = str(status_raw or "").strip().lower().replace(" ", "_")

        if status in (
            "realizado",
            "concluido",
            "concluído",
            "saiu",
            "finalizado",
            "liberado",
        ):
            return "realizado"

        return "pendente"

    def _status_indica_pendente(self, status_raw):
        status = str(status_raw or "").strip().lower().replace(" ", "_")

        return status in (
            "pendente",
            "aguardando",
            "aberto",
            "ativo",
            "entrada",
            "nova_entrada",
            "novo",
            "em_andamento",
            "presente",
        )

    def _status_indica_realizado(self, status_raw):
        status = str(status_raw or "").strip().lower().replace(" ", "_")

        return status in (
            "realizado",
            "concluido",
            "concluído",
            "saiu",
            "finalizado",
            "liberado",
        )

    def _parse_data_hora(self, data_valor=None, hora_valor=None):
        if isinstance(data_valor, datetime):
            return data_valor

        data_txt = str(data_valor or "").strip()
        hora_txt = str(hora_valor or "").strip()

        if not data_txt:
            return None

        candidatos = []

        if hora_txt:
            candidatos.append(f"{data_txt} {hora_txt}")

        candidatos.append(data_txt)

        formatos = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y",
        ]

        for texto in candidatos:
            try:
                return datetime.fromisoformat(texto)
            except Exception:
                pass

            for formato in formatos:
                try:
                    return datetime.strptime(texto, formato)
                except Exception:
                    continue

        return None

    def _parse_datetime_generico(self, valor):
        if not valor:
            return None

        if isinstance(valor, datetime):
            return valor

        texto = str(valor).strip()
        if not texto:
            return None

        formatos = [
            None,
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y",
        ]

        for formato in formatos:
            try:
                if formato is None:
                    return datetime.fromisoformat(texto)
                return datetime.strptime(texto, formato)
            except Exception:
                continue

        return None

    def _registro_foi_reaberto(
        self,
        status_base,
        data_evento=None,
        concluido_em=None,
        concluido_no_sistema=False,
        status_balgate="",
    ):
        data_evento_dt = self._parse_datetime_generico(data_evento)
        concluido_em_dt = self._parse_datetime_generico(concluido_em)
        status_balgate_norm = str(status_balgate or "").strip().lower().replace(" ", "_")
        status_base_norm = str(status_base or "").strip().lower().replace(" ", "_")

        # nova entrada explícita sempre volta para pendente
        if status_base_norm == "nova_entrada":
            return True

        # se já existe conclusão registrada, só reabre com evidência real de evento mais novo
        possui_conclusao = bool(
            concluido_no_sistema
            or concluido_em_dt
            or status_balgate_norm == "realizado"
        )

        if possui_conclusao:
            if data_evento_dt and concluido_em_dt:
                return data_evento_dt > concluido_em_dt
            return False

        # se nunca houve conclusão, os status pendentes continuam pendentes
        return self._status_indica_pendente(status_base_norm)

    def _obter_primeiro_individuo(self, consumo):
        individuos = consumo.get("individuos") or []

        if isinstance(individuos, list):
            for item in individuos:
                if isinstance(item, dict):
                    return item

        if isinstance(individuos, dict):
            for chave in sorted(individuos.keys(), key=lambda x: str(x)):
                item = individuos.get(chave)
                if isinstance(item, dict):
                    return item

        return {}

    def _status_base_consumo(self, c, individuo):
        status_individuo = str(individuo.get("status") or "").strip().lower().replace(" ", "_")
        status_cadastro = str(c.get("status") or "").strip().lower().replace(" ", "_")

        if self._status_indica_pendente(status_individuo):
            return status_individuo

        if self._status_indica_realizado(status_individuo):
            return status_individuo

        if self._status_indica_pendente(status_cadastro):
            return status_cadastro

        if self._status_indica_realizado(status_cadastro):
            return status_cadastro

        return status_cadastro or status_individuo or ""

    def _chave_registro(self, origem, registro_id):
        return (str(origem or "").strip().lower(), str(registro_id or "").strip())

    def _limpar_conclusoes_recentes_expiradas(self):
        agora = datetime.now()
        chaves_expiradas = [
            chave
            for chave, data_limite in self._conclusoes_recentes.items()
            if data_limite <= agora
        ]

        for chave in chaves_expiradas:
            self._conclusoes_recentes.pop(chave, None)

    def _marcar_conclusao_recente(self, origem, registro_id):
        if not registro_id:
            return

        self._limpar_conclusoes_recentes_expiradas()
        self._conclusoes_recentes[self._chave_registro(origem, registro_id)] = (
            datetime.now() + self._janela_protecao_conclusao
        )

    def _registro_em_janela_de_conclusao(self, origem, registro_id):
        self._limpar_conclusoes_recentes_expiradas()
        return self._chave_registro(origem, registro_id) in self._conclusoes_recentes

    # ------------------------------------------------------------------
    # VISITANTES
    # ------------------------------------------------------------------
    def converter_visitante_para_cadastro(self, v):
        registro_id = v.get("id", "")

        data_evento = self._pick(v, "dataEntrada", "data")
        hora_evento = self._pick(v, "horaEntrada", "hora")
        datahora_evento_dt = self._parse_data_hora(data_evento, hora_evento)
        datahora_evento = (
            datahora_evento_dt.isoformat()
            if datahora_evento_dt
            else f"{data_evento} {hora_evento}".strip()
        )

        status_base = v.get("status", "")
        status_balgate = v.get("status_balgate", "")
        concluido_em_origem = self._pick(v, "concluido_em", "concluidoEm")
        concluido_no_sistema = bool(v.get("concluido_no_sistema"))

        conclusao_local = None
        if self.db_ok and self.db is not None:
            try:
                conclusao_local = self.db.obter_conclusao_local("visitantes", registro_id)
            except Exception:
                conclusao_local = None

        em_janela_protecao = self._registro_em_janela_de_conclusao("visitantes", registro_id)

        foi_reaberto = self._registro_foi_reaberto(
            status_base=status_base,
            data_evento=datahora_evento,
            concluido_em=(concluido_em_origem or conclusao_local),
            concluido_no_sistema=(concluido_no_sistema or bool(conclusao_local) or em_janela_protecao),
            status_balgate=(status_balgate or ("realizado" if conclusao_local or em_janela_protecao else "")),
        )

        if foi_reaberto:
            status_final = "pendente"
            smartcard_final = ""
            concluido_em_final = ""
            status_balgate_final = ""
            concluido_no_sistema_final = False
        elif em_janela_protecao or conclusao_local:
            status_final = "realizado"
            smartcard_final = self._pick(v, "smartcard")
            concluido_em_final = concluido_em_origem or conclusao_local
            status_balgate_final = "REALIZADO"
            concluido_no_sistema_final = True
        else:
            status_final = (
                self._normalizar_status(status_balgate)
                if str(status_balgate).strip()
                else self._normalizar_status(status_base)
            )
            smartcard_final = self._pick(v, "smartcard")
            concluido_em_final = concluido_em_origem
            status_balgate_final = self._pick(v, "status_balgate")
            concluido_no_sistema_final = concluido_no_sistema

        cadastro = {
            "id": registro_id,
            "id_original": registro_id,
            "origem": "visitantes",

            "placa": self._pick(v, "placa"),

            "motorista_nome": self._pick(v, "motorista_nome", "nome"),
            "motorista_cnh": self._pick(v, "motorista_cnh", "cnh"),
            "motorista_validade_cnh": self._pick(v, "motorista_validade_cnh", "validadeCnh"),
            "motorista_categoria_cnh": self._pick(v, "categoriaCnh"),
            "motorista_data_nascimento": self._pick(v, "dataNascimento"),
            "motorista_cpf": self._pick(v, "motorista_cpf", "documento"),
            "motorista_rg": self._pick(v, "motorista_rg", "rg"),
            "motorista_validade_rg": self._pick(v, "motorista_validade_rg", "validadeRg", "rg_validade"),
            "motorista_telefone": self._pick(v, "motorista_telefone", "telefone"),

            "empresa_motorista": self._pick(v, "empresa_motorista", "empresa"),
            "empresa_solicitante": self._pick(v, "empresa_solicitante", "destino"),

            "tipo_operacao": self._pick(v, "tipo_operacao"),
            "servico_terminal": self._pick(v, "servico_terminal", "motivo"),
            "nota_fiscal": self._pick(v, "nota_fiscal", "notaFiscal"),

            "data": data_evento,
            "hora": hora_evento,
            "datahora_evento": datahora_evento,
            "concluido_em": concluido_em_final,

            "smartcard": smartcard_final,

            "status": status_final,
            "status_balgate": status_balgate_final,
            "concluido_no_sistema": concluido_no_sistema_final,
        }

        return cadastro

    # ------------------------------------------------------------------
    # CONSUMOS
    # ------------------------------------------------------------------
    def converter_consumo_para_cadastro(self, c):
        individuo = self._obter_primeiro_individuo(c)

        registro_id = c.get("id", "")

        data_evento = (
            self._pick(c, "dataEntrada", "data")
            or self._pick(individuo, "dataEntrada", "data")
        )
        hora_evento = (
            self._pick(c, "horaEntrada", "hora")
            or self._pick(individuo, "horaEntrada", "hora")
        )

        datahora_evento_dt = self._parse_data_hora(data_evento, hora_evento)
        datahora_evento = (
            datahora_evento_dt.isoformat()
            if datahora_evento_dt
            else f"{data_evento} {hora_evento}".strip()
        )

        status_base = self._status_base_consumo(c, individuo)
        status_balgate = c.get("status_balgate", "")
        concluido_em_origem = self._pick(c, "concluido_em", "concluidoEm")
        concluido_no_sistema = bool(c.get("concluido_no_sistema"))

        conclusao_local = None
        if self.db_ok and self.db is not None:
            try:
                conclusao_local = self.db.obter_conclusao_local("consumos", registro_id)
            except Exception:
                conclusao_local = None

        em_janela_protecao = self._registro_em_janela_de_conclusao("consumos", registro_id)

        foi_reaberto = self._registro_foi_reaberto(
            status_base=status_base,
            data_evento=datahora_evento,
            concluido_em=(concluido_em_origem or conclusao_local),
            concluido_no_sistema=(concluido_no_sistema or bool(conclusao_local) or em_janela_protecao),
            status_balgate=(status_balgate or ("realizado" if conclusao_local or em_janela_protecao else "")),
        )

        empresa_motorista = (
            self._pick(individuo, "empresa_motorista", "empresa")
            or self._pick(c, "empresa_motorista", "empresa")
        )

        tipo_operacao = (
            self._pick(c, "tipo_operacao", "destino", "tipoServico")
            or self._pick(individuo, "tipo_operacao", "destino")
        )

        servico_terminal = (
            self._pick(c, "servico_terminal", "motivo", "tipoServico", "produto", "terminal")
            or self._pick(individuo, "servico_terminal", "motivo")
        )

        if foi_reaberto:
            status_final = "pendente"
            smartcard_final = ""
            concluido_em_final = ""
            status_balgate_final = ""
            concluido_no_sistema_final = False
        elif em_janela_protecao or conclusao_local:
            status_final = "realizado"
            smartcard_final = self._pick(c, "smartcard")
            concluido_em_final = concluido_em_origem or conclusao_local
            status_balgate_final = "REALIZADO"
            concluido_no_sistema_final = True
        else:
            status_final = (
                self._normalizar_status(status_balgate)
                if str(status_balgate).strip()
                else self._normalizar_status(status_base)
            )
            smartcard_final = self._pick(c, "smartcard")
            concluido_em_final = concluido_em_origem
            status_balgate_final = self._pick(c, "status_balgate")
            concluido_no_sistema_final = concluido_no_sistema

        cadastro = {
            "id": registro_id,
            "id_original": registro_id,
            "origem": "consumos",

            "placa": self._pick(c, "placa"),

            "motorista_nome": self._pick(individuo, "motorista_nome", "nome"),
            "motorista_cnh": self._pick(individuo, "motorista_cnh", "cnh"),
            "motorista_validade_cnh": self._pick(individuo, "motorista_validade_cnh", "validadeCnh"),
            "motorista_categoria_cnh": self._pick(individuo, "motorista_categoria_cnh", "categoriaCnh"),
            "motorista_data_nascimento": self._pick(individuo, "motorista_data_nascimento", "dataNascimento"),
            "motorista_cpf": self._pick(individuo, "motorista_cpf", "documento"),
            "motorista_rg": self._pick(individuo, "motorista_rg", "rg"),
            "motorista_validade_rg": self._pick(individuo, "motorista_validade_rg", "validadeRg", "rg_validade"),
            "motorista_telefone": self._pick(individuo, "motorista_telefone", "telefone"),

            "empresa_motorista": empresa_motorista,
            "tipo_operacao": tipo_operacao,
            "servico_terminal": servico_terminal,
            "nota_fiscal": self._pick(c, "nota_fiscal", "notaFiscal"),

            "data": data_evento,
            "hora": hora_evento,
            "datahora_evento": datahora_evento,
            "concluido_em": concluido_em_final,

            "smartcard": smartcard_final,

            "status": status_final,
            "status_balgate": status_balgate_final,
            "concluido_no_sistema": concluido_no_sistema_final,

            "navio": self._pick(c, "navio"),
            "produto": self._pick(c, "produto"),
            "terminal": self._pick(c, "terminal"),
            "veiculo": self._pick(c, "veiculo"),
            "vigilante": self._pick(c, "vigilante"),
            "credencial": self._pick(individuo, "credencial"),
        }

        return cadastro

    # ------------------------------------------------------------------
    # CONCLUIR
    # ------------------------------------------------------------------
    def concluir_cadastro(self, cadastro, smartcard):
        if not self.firebase_ok:
            raise RuntimeError(
                self.erro_firebase or
                "Firebase ainda não inicializado."
            )

        registro_id = cadastro.get("id_original") or cadastro.get("id")
        origem = cadastro.get("origem", "visitantes")

        if not registro_id:
            raise ValueError("Cadastro sem ID válido para conclusão.")

        agora = datetime.now().isoformat()

        atualizacao = {
            "status_balgate": "realizado",
            "smartcard": smartcard,
            "concluidoEm": agora,
            "concluido_no_sistema": True,
        }

        sucesso = self.client.atualizar_registro(origem, registro_id, atualizacao)

        if not sucesso:
            raise RuntimeError(
                f"Não foi possível atualizar o Firebase para {origem}/{registro_id}."
            )

        cadastro["status"] = "realizado"
        cadastro["smartcard"] = smartcard
        cadastro["concluido_em"] = agora
        cadastro["status_balgate"] = "realizado"
        cadastro["concluido_no_sistema"] = True

        if self.db_ok and self.db is not None:
            try:
                self.db.upsert_ficha(
                    origem=origem,
                    registro_id=registro_id,
                    status="realizado",
                    concluido_em_local=agora,
                )
            except Exception:
                pass

        self._marcar_conclusao_recente(origem, registro_id)

        self.cadastros_pendentes = [
            c for c in self.cadastros_pendentes
            if not (
                c.get("origem") == cadastro.get("origem")
                and c.get("id") == cadastro.get("id")
            )
        ]

        self.cadastros_realizados = [
            c for c in self.cadastros_realizados
            if not (
                c.get("origem") == cadastro.get("origem")
                and c.get("id") == cadastro.get("id")
            )
        ]

        # recém concluída entra no topo
        self.cadastros_realizados.insert(0, dict(cadastro))

        return cadastro
