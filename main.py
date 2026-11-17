from machine import Pin
from time import sleep_us, sleep_ms
import json

ARQUIVO_CONFIG = "config.json"

# ==========================================
# CONFIGURACOES DO SISTEMA
# ==========================================

# Pinos ESP32-C3 -> A4988
PIN_ENABLE = 5
PIN_MS1 = 4
PIN_MS2 = 3
PIN_MS3 = 2
PIN_STEP = 1
PIN_DIR = 0

# Motor de passo
ANGULO_PASSO = 1.8
MICROPASSO = 16        # valor inicial: 1, 2, 4, 8, 16

# Fuso
AVANCO_FUSO = 2.0      # mm por revolucao

# Velocidade linear inicial
VELOCIDADE = 2.0       # mm/s
VELOCIDADE_MAX = 50.0  # limite de seguranca (mm/s)

# Sentido de movimento
SENTIDO_PADRAO = 1     # 1 ou 0

# Tempo de pulso STEP (microssegundos)
PULSO_STEP_US = 5

HABILITADO_INICIAL = True

# Tabela divisor -> (MS1, MS2, MS3) do A4988
TABELA_MS = {
    1:  (0, 0, 0),
    2:  (1, 0, 0),
    4:  (0, 1, 0),
    8:  (1, 1, 0),
    16: (1, 1, 1),
}

# Tabela inversa: (MS1, MS2, MS3) -> divisor
TABELA_MS_INV = {v: k for k, v in TABELA_MS.items()}
TABELA_MS_INV[(0, 0, 1)] = 16
TABELA_MS_INV[(0, 1, 1)] = 16
TABELA_MS_INV[(1, 0, 1)] = 16


def salvar_config():
    """Salva configuracoes em arquivo JSON."""
    cfg = {
        "micropasso": MICROPASSO,
        "velocidade": VELOCIDADE,
        "sentido": SENTIDO_PADRAO,
        "habilitado": habilitado,
    }
    try:
        with open(ARQUIVO_CONFIG, "w") as f:
            json.dump(cfg, f)
    except Exception as e:
        print(f"Erro ao salvar configuração: {e}")


def carregar_config():
    """Carrega configuracoes de arquivo JSON."""
    global MICROPASSO, VELOCIDADE, SENTIDO_PADRAO, HABILITADO_INICIAL
    try:
        with open(ARQUIVO_CONFIG, "r") as f:
            cfg = json.load(f)

        m = cfg.get("micropasso", MICROPASSO)
        if m in TABELA_MS:
            MICROPASSO = m

        v = cfg.get("velocidade", VELOCIDADE)
        if isinstance(v, (int, float)) and 0 < v <= VELOCIDADE_MAX:
            VELOCIDADE = float(v)

        s = cfg.get("sentido", SENTIDO_PADRAO)
        if s in (0, 1):
            SENTIDO_PADRAO = s

        h = cfg.get("habilitado", HABILITADO_INICIAL)
        if isinstance(h, bool):
            HABILITADO_INICIAL = h

        print("Configuracao carregada da flash.")
    except OSError:
        print("Arquivo de configuracao nao encontrado. Usando valores padrao.")
    except Exception as e:
        print("Erro ao carregar configuracao:", e)


# ==========================================
# INICIALIZACAO DO HARDWARE
# ==========================================

step = Pin(PIN_STEP, Pin.OUT, value=0)
direcao = Pin(PIN_DIR, Pin.OUT, value=SENTIDO_PADRAO)
enable = Pin(PIN_ENABLE, Pin.OUT, value=1)  # desabilitado ate configurar
ms1 = Pin(PIN_MS1, Pin.OUT)
ms2 = Pin(PIN_MS2, Pin.OUT)
ms3 = Pin(PIN_MS3, Pin.OUT)

# Estado
habilitado = False
micropassos_mm = 0.0
intervalo_step_us = 0
posicao_mm = 0.0       # <--- NOVO: rastreia a posicao atual em mm


# ==========================================
# FUNCOES DE CONFIGURACAO
# ==========================================

def recalcular():
    """Recalcula parametros que dependem de micropasso e velocidade."""
    global micropassos_mm, intervalo_step_us

    passos_rev = 360 / ANGULO_PASSO
    micropassos_rev = passos_rev * MICROPASSO
    micropassos_mm = micropassos_rev / AVANCO_FUSO

    frequencia = VELOCIDADE * micropassos_mm
    intervalo_step_us = int(1_000_000 / frequencia)


def aplicar_micropasso(divisor, pinos=None):
    """Aplica o micropasso nos pinos MS. 'pinos' permite forcar (ms1, ms2, ms3)."""
    global MICROPASSO

    if pinos is None:
        pinos = TABELA_MS[divisor]

    ms1.value(pinos[0])
    ms2.value(pinos[1])
    ms3.value(pinos[2])
    MICROPASSO = divisor
    sleep_ms(1)
    recalcular()


def habilitar(estado):
    global habilitado
    enable.value(0 if estado else 1)  # ENABLE ativo em LOW
    habilitado = estado


def validar_velocidade(v):
    """Verifica se a velocidade e viavel para o micropasso atual."""
    if v <= 0 or v > VELOCIDADE_MAX:
        return False
    freq = v * micropassos_mm
    intervalo = 1_000_000 / freq
    return intervalo >= 2 * PULSO_STEP_US + 20


def zerar_posicao():
    """Define a posicao atual como origem (0.0 mm)."""
    global posicao_mm
    posicao_mm = 0.0


# ==========================================
# MOVIMENTO
# ==========================================

def mover(distancia_mm):
    global posicao_mm

    if not habilitado:
        print("ERRO: driver desabilitado. Use EN antes de mover.")
        return

    if distancia_mm == 0:
        print("Distancia zero.")
        return

    sinal = 1 if distancia_mm > 0 else -1
    if sinal > 0:
        direcao.value(SENTIDO_PADRAO)
    else:
        direcao.value(1 - SENTIDO_PADRAO)

    distancia = abs(distancia_mm)
    passos = round(distancia * micropassos_mm)
    distancia_comandada = passos / micropassos_mm

    print("\nMovimento iniciado")
    print("Distancia solicitada: %.6f mm" % distancia_mm)
    print("Micropassos: %d" % passos)
    print("Distancia quantizada: %.6f mm" % (sinal * distancia_comandada))

    sleep_us(10)  # estabilizacao do DIR

    restante = intervalo_step_us - PULSO_STEP_US

    for i in range(passos):
        step.value(1)
        sleep_us(PULSO_STEP_US)
        step.value(0)
        if restante > 0:
            sleep_us(restante)

    # Atualiza a posicao usando o deslocamento real executado
    posicao_mm += sinal * distancia_comandada
    print("Movimento concluido | Posicao atual: %.4f mm" % posicao_mm)


def mover_para(alvo_mm):
    """Move para uma coordenada absoluta em relacao ao zero."""
    deslocamento = alvo_mm - posicao_mm
    mover(deslocamento)


# ==========================================
# INTERPRETADOR DE COMANDOS
# ==========================================

def mostrar_status():
    p = (ms1.value(), ms2.value(), ms3.value())
    print("--- STATUS ---")
    print("Driver:", "HABILITADO" if habilitado else "DESABILITADO")
    print("Posicao atual: %.4f mm" % posicao_mm)
    print("Micropasso: 1/%d (MS1=%d MS2=%d MS3=%d)" % (MICROPASSO, p[0], p[1], p[2]))
    print("Resolucao: %.2f micropassos/mm" % micropassos_mm)
    print("Velocidade: %.3f mm/s" % VELOCIDADE)
    print("Intervalo entre pulsos: %d us" % intervalo_step_us)


def mostrar_ajuda():
    print("--- COMANDOS ---")
    print("EN                    habilita o driver")
    print("DIS                   desabilita o driver")
    print("ZERO                  define o ponto atual como zero (0.0 mm)")
    print("DIST,<mm>             move distancia relativa (negativo inverte)")
    print("POS,<mm>              move para posicao absoluta em relacao ao zero")
    print("MP,<divisor>          micropasso: 1, 2, 4, 8, 16")
    print("MP,<ms1>,<ms2>,<ms3>  micropasso pelos pinos MS (ex: MP,1,0,0)")
    print("VEL,<mm/s>            define a velocidade")
    print("STATUS                mostra configuracao e posicao")
    print("HELP                  mostra esta ajuda")
    print("Use ';' para encadear: ZERO;DIST,15;POS,0")


def executar(comando):
    global VELOCIDADE

    partes = [p.strip() for p in comando.upper().split(",")]
    nome = partes[0]
    args = partes[1:]

    if nome == "EN":
        habilitar(True)
        salvar_config()
        print("OK: driver habilitado")

    elif nome == "DIS":
        habilitar(False)
        salvar_config()
        print("OK: driver desabilitado")

    elif nome == "ZERO":
        zerar_posicao()
        print("OK: posicao atual definida como 0.0000 mm")

    elif nome == "DIST":
        if len(args) != 1:
            print("ERRO: uso -> DIST,<mm>")
            return
        mover(float(args[0]))

    elif nome == "POS":
        if len(args) != 1:
            print("ERRO: uso -> POS,<mm>")
            return
        mover_para(float(args[0]))

    elif nome == "MP":
        if len(args) == 1:
            divisor = int(args[0])
            if divisor not in TABELA_MS:
                print("ERRO: divisor invalido. Use 1, 2, 4, 8 ou 16.")
                return
            aplicar_micropasso(divisor)

        elif len(args) == 3:
            pinos = tuple(int(a) for a in args)
            if any(p not in (0, 1) for p in pinos):
                print("ERRO: MS1, MS2 e MS3 devem ser 0 ou 1.")
                return
            aplicar_micropasso(TABELA_MS_INV[pinos], pinos)

        else:
            print("ERRO: uso -> MP,<divisor> ou MP,<ms1>,<ms2>,<ms3>")
            return

        if not validar_velocidade(VELOCIDADE):
            print("AVISO: velocidade atual inviavel neste micropasso. Reduza com VEL.")
        salvar_config()
        print("OK: micropasso 1/%d (%.2f micropassos/mm)" % (MICROPASSO, micropassos_mm))

    elif nome == "VEL":
        if len(args) != 1:
            print("ERRO: uso -> VEL,<mm/s>")
            return
        v = float(args[0])
        if not validar_velocidade(v):
            print("ERRO: velocidade fora do limite (max %.1f mm/s ou rapida demais)." % VELOCIDADE_MAX)
            return
        VELOCIDADE = v
        recalcular()
        salvar_config()
        print("OK: velocidade %.3f mm/s" % VELOCIDADE)

    elif nome == "STATUS":
        mostrar_status()

    elif nome == "HELP":
        mostrar_ajuda()

    elif nome == "":
        pass

    else:
        print("ERRO: comando desconhecido '%s'. Digite HELP." % nome)


# ==========================================
# INICIO
# ==========================================
carregar_config()
aplicar_micropasso(MICROPASSO)
habilitar(HABILITADO_INICIAL)

print("\n=== CONTROLE LINEAR NEMA17 ===")
mostrar_status()
print("Digite HELP para ver os comandos.\n")

while True:
    try:
        linha = input("> ")

        for cmd in linha.split(";"):
            try:
                executar(cmd)
            except ValueError:
                print("ERRO: valor numerico invalido em '%s'." % cmd.strip())

    except KeyboardInterrupt:
        habilitar(False)
        salvar_config()
        print("\nDriver desabilitado.")
        break