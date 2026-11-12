
#!/usr/bin/env python3

import math
import time

import rclpy
from rclpy.node import Node

from std_msgs.msg import (
    Float64MultiArray,
    String,
    Bool
)

import serial


class EnergyMonitor(Node):

    def __init__(self):
        super().__init__('avant_energy_monitor')

        # ===================================
        # PARAMETROS
        # ===================================

        self.declare_parameter(
            'serial_port', '/dev/ttyTHS1'
        )
        self.declare_parameter(
            'baud_rate', 115200
        )
        self.declare_parameter(
            'timeout_conexao', 3.0
        )

        self.porta = self.get_parameter(
            'serial_port'
        ).value

        self.baud = self.get_parameter(
            'baud_rate'
        ).value

        self.timeout_conexao = self.get_parameter(
            'timeout_conexao'
        ).value

        # ===================================
        # IDENTIFICACAO DOS SENSORES
        # ===================================

        self.nomes = [
            'bateria',
            'esc1',
            'esc2',
            'esc3',
            'esc4'
        ]

        # ===================================
        # PUBLICADORES ROS2
        # ===================================

        self.publishers = {}

        for nome in self.nomes:

            topico = f'/avant/energia/{nome}'

            self.publishers[nome] = (
                self.create_publisher(
                    Float64MultiArray,
                    topico,
                    10
                )
            )

        self.alert_pub = self.create_publisher(
            String,
            '/avant/energia/alertas',
            10
        )

        self.connection_pub = self.create_publisher(
            Bool,
            '/avant/energia/conexao',
            10
        )

        # ===================================
        # ESTADO DA COMUNICACAO
        # ===================================

        self.uart = None
        self.buffer = bytearray()

        self.conectado = False

        self.ultima_mensagem = None
        self.ultima_tentativa = 0.0

        # 50 Hz para consultar o buffer UART
        self.timer = self.create_timer(
            0.02,
            self.ler_uart
        )

        # Verificacao periodica de timeout
        self.watchdog = self.create_timer(
            0.5,
            self.verificar_conexao
        )

        self.get_logger().info(
            'Monitoramento de energia AVANT iniciado'
        )

        self.abrir_uart()

    # =======================================
    # ABRIR COMUNICACAO UART
    # =======================================

    def abrir_uart(self):

        self.ultima_tentativa = time.monotonic()

        try:
            self.uart = serial.Serial(
                port=self.porta,
                baudrate=self.baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0
            )

            self.buffer.clear()

            self.get_logger().info(
                f'UART aberta: {self.porta} '
                f'({self.baud} baud)'
            )

        except serial.SerialException as erro:

            self.uart = None

            self.get_logger().error(
                f'Erro ao abrir UART: {erro}'
            )

    # =======================================
    # PUBLICAR ESTADO DA CONEXAO
    # =======================================

    def atualizar_conexao(self, estado):

        if self.conectado == estado:
            return

        self.conectado = estado

        msg = Bool()
        msg.data = estado

        self.connection_pub.publish(msg)

        if estado:
            self.get_logger().info(
                'ESP32 conectado e transmitindo'
            )
        else:
            self.get_logger().warning(
                'Comunicacao com ESP32 perdida'
            )

            self.publicar_alerta(
                'ERROR,ESP32,FALHA_COMUNICACAO'
            )

    # =======================================
    # LER UART
    # =======================================

    def ler_uart(self):

        # Tentar reconectar caso a porta esteja fechada
        if self.uart is None:

            if (
                time.monotonic() -
                self.ultima_tentativa >= 2.0
            ):
                self.abrir_uart()

            return

        try:

            quantidade = self.uart.in_waiting

            if quantidade == 0:
                return

            # Leitura sem bloqueio
            recebido = self.uart.read(
                min(quantidade, 1024)
            )

            self.buffer.extend(recebido)

            # Protecao contra buffer excessivo
            if len(self.buffer) > 4096:
                self.buffer.clear()

                self.get_logger().warning(
                    'Buffer UART excedido'
                )
                return

            # Separar as mensagens por quebra de linha
            while b'\n' in self.buffer:

                linha, _, restante = (
                    self.buffer.partition(b'\n')
                )

                self.buffer = bytearray(restante)

                texto = linha.decode(
                    'utf-8',
                    errors='replace'
                ).strip()

                if texto:
                    self.processar_mensagem(texto)

        except (serial.SerialException, OSError) as erro:

            self.get_logger().error(
                f'Falha de comunicacao UART: {erro}'
            )

            self.fechar_uart()
            self.atualizar_conexao(False)

    # =======================================
    # PROCESSAR MENSAGENS
    # =======================================

    def processar_mensagem(self, linha):

        partes = linha.split(',')

        tipo = partes[0]

        if tipo == 'DATA':

            self.processar_dados(partes)

        elif tipo == 'WARN':

            if len(partes) == 3:

                self.publicar_alerta(linha)

                self.get_logger().warning(
                    f'{partes[1]}: {partes[2]}'
                )

        elif tipo == 'ERROR':

            if len(partes) == 3:

                self.publicar_alerta(linha)

                self.get_logger().error(
                    f'{partes[1]}: {partes[2]}'
                )

    # =======================================
    # PROCESSAR 5 INA228
    # =======================================

   
def processar_dados(self, partes):

    # DATA + 5 sensores x 3 valores
    if len(partes) != 16:
        self.get_logger().warning(
            'Pacote DATA incompleto'
        )
        return

    medicoes = []

    try:
        for i in range(5):

            indice = 1 + (i * 3)

            tensao = float(partes[indice])
            corrente = float(partes[indice + 1])
            validade = int(partes[indice + 2])

            if validade not in (0, 1):
                raise ValueError('Validade invalida')

            if not (
                math.isfinite(tensao)
                and math.isfinite(corrente)
            ):
                raise ValueError('Medicao invalida')

            medicoes.append(
                (tensao, corrente, validade)
            )

    except (ValueError, IndexError):
        self.get_logger().warning(
            'Pacote com valores invalidos'
        )
        return

    # Publicar e imprimir medicoes
    for nome, medicao in zip(self.nomes, medicoes):

        tensao, corrente, valido = medicao

        msg = Float64MultiArray()

        if valido:

            potencia = tensao * corrente

            msg.data = [
                tensao,
                corrente,
                1.0
            ]

            # LOG INFO
            self.get_logger().info(
                f'{nome.upper():8s} | '
                f'Tensao: {tensao:7.3f} V | '
                f'Corrente: {corrente:8.3f} A | '
                f'Potencia: {potencia:9.3f} W'
            )

        else:

            msg.data = [
                float('nan'),
                float('nan'),
                0.0
            ]

            self.get_logger().warning(
                f'{nome.upper()} | '
                'Leitura indisponivel'
            )

        self.publishers[nome].publish(msg)

    # Atualizar watchdog
    self.ultima_mensagem = time.monotonic()
    self.atualizar_conexao(True)


    def publicar_alerta(self, texto):

        msg = String()
        msg.data = texto

        self.alert_pub.publish(msg)


    def verificar_conexao(self):

        if self.ultima_mensagem is None:
            return

        tempo_sem_dados = (
            time.monotonic() -
            self.ultima_mensagem
        )

        if tempo_sem_dados > self.timeout_conexao:

            self.atualizar_conexao(False)


    def fechar_uart(self):

        if self.uart is not None:

            try:
                self.uart.close()
            except (serial.SerialException, OSError):
                pass

            self.uart = None

        self.buffer.clear()

    def destroy_node(self):

        self.fechar_uart()
        super().destroy_node()

def main(args=None):

    rclpy.init(args=args)

    node = EnergyMonitor()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
