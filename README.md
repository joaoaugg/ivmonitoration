# AVANT x CADENCE Energy Monitor

Sistema de monitoramento elétrico desenvolvido para a equipe **AVANT – UFMG**, utilizando ESP32, sensores INA228 e NVIDIA Jetson com ROS2.

O projeto tem como objetivo monitorar em tempo real a tensão, corrente e potência da bateria e dos quatro ESCs de um drone autônomo.

## 1. Funcionamento

O sistema utiliza cinco sensores INA228 conectados ao ESP32 através do protocolo I²C.

O ESP32 realiza a aquisição das medições e transmite os dados para a Jetson por comunicação UART (TX/RX), utilizando uma taxa de 115200 baud.

Na Jetson, um nó ROS2 recebe as informações, calcula a potência elétrica e publica os dados em tópicos individuais.

**Grandezas monitoradas:**
- Tensão (V)
- Corrente (A)
- Potência (W)

**Componentes monitorados:**
- Bateria
- ESC 1
- ESC 2
- ESC 3
- ESC 4

## 2. Hardware

| Componentes Base do Projeto | Quantidade |
|---|---:|
| ESP32 | 1 |
| INA228 | 5 |
| Resistor shunt | 5 |
| NVIDIA Jetson | 1 |

### Configuração dos sensores

| Sensor | Endereço I²C |
|---|---|
| Bateria | `0x40` |
| ESC 1 | `0x41` |
| ESC 2 | `0x42` |
| ESC 3 | `0x43` |
| ESC 4 | `0x44` |

### Comunicação

- **INA228 → ESP32:** I²C
- **ESP32 → Jetson:** UART (TX/RX)
- **Jetson:** ROS2 Humble

## 3. Software

O projeto está dividido em dois módulos:

**ESP32 (Arduino/C++)**
- Aquisição dos sensores INA228.
- Verificação da alimentação elétrica.
- Identificação de falhas I²C.
- Transmissão das medições via UART.

**Jetson (Python/ROS2)**
- Recepção e processamento dos dados.
- Cálculo da potência elétrica.
- Publicação das informações em tópicos ROS2.
- Exibição das medições no terminal por `LOG INFO`.
- Monitoramento de falhas e perda de comunicação.

## 4. Tópicos ROS2

| Tópico | Informação |
|---|---|
| `/avant/energia/bateria` | Medições da bateria |
| `/avant/energia/esc1` | Medições do ESC 1 |
| `/avant/energia/esc2` | Medições do ESC 2 |
| `/avant/energia/esc3` | Medições do ESC 3 |
| `/avant/energia/esc4` | Medições do ESC 4 |
| `/avant/energia/alertas` | Avisos e erros |
| `/avant/energia/conexao` | Estado da comunicação |

## 5. Execução

### Instalar dependências

```bash
sudo apt install python3-serial
```

### Compilar o pacote

```bash
cd ~/ros2_ws
colcon build --packages-select avant_energy_monitor
source install/setup.bash
```

### Executar o nó

```bash
ros2 run avant_energy_monitor energy_node \
  --ros-args -p serial_port:=/dev/ttyTHS1
```

A porta serial deve ser ajustada conforme a configuração da Jetson.

### Visualizar medições

```bash
ros2 topic echo /avant/energia/bateria
```

O terminal também apresenta continuamente tensão, corrente e potência de todos os sensores.

## 6. Melhorias futuras

- [ ] Implementação de novos sensores para monitoramento de outros componentes eletrônicos do drone.
- [ ] Monitoramento de temperatura da bateria, ESCs e motores.
- [ ] Integração de sensores para acompanhamento do estado de carga da bateria.
- [ ] Monitoramento de vibração dos motores e da estrutura.
- [ ] Desenvolvimento de sistemas de alerta para condições elétricas anormais.
- [ ] Armazenamento e análise dos dados durante os voos.
- [ ] Integração com uma interface gráfica de monitoramento em tempo real.

---

**AVANT – UFMG | Projeto de Monitoramento Elétrico Embarcado**
