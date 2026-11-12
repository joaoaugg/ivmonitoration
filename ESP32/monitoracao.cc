
//bibliotecas
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_INA228.h>

#define SDA_PIN 21
#define SCL_PIN 22

#define UART_RX 16
#define UART_TX 17

#define BAUD_RATE 115200

#define NUM_SENSORES 5
#define TENSAO_MINIMA 0.5f
#define INTERVALO_MS 1000

//ina228

const uint8_t enderecos[NUM_SENSORES] = {
  0x40, // Bateria
  0x41, // ESC 1
  0x42, // ESC 2
  0x43, // ESC 3
  0x44  // ESC 4
};

const char* nomes[NUM_SENSORES] = {
  "BATERIA",
  "ESC1",
  "ESC2",
  "ESC3",
  "ESC4"
};

// shunt = 1m
const float shuntOhms[NUM_SENSORES] = {
  0.001f,
  0.001f,
  0.001f,
  0.001f,
  0.001f
};

// corrente máxima
const float correnteMaxA[NUM_SENSORES] = {
  80.0f,
  80.0f,
  80.0f,
  80.0f,
  80.0f
};

Adafruit_INA228 ina0;
Adafruit_INA228 ina1;
Adafruit_INA228 ina2;
Adafruit_INA228 ina3;
Adafruit_INA228 ina4;

Adafruit_INA228* sensores[NUM_SENSORES] = {
  &ina0, &ina1, &ina2, &ina3, &ina4
};

// dados

struct Medicao {
  float tensao;
  float corrente;
  bool valido;
};

Medicao dados[NUM_SENSORES];

unsigned long ultimaLeitura = 0;

// i2c

bool verificarI2C(uint8_t endereco) {
  Wire.beginTransmission(endereco);
  return Wire.endTransmission() == 0;
}

// iniciando sensores

bool iniciarINA(int i) {

  if (!verificarI2C(enderecos[i])) {
    return false;
  }

  if (!sensores[i]->begin(enderecos[i], &Wire)) {
    return false;
  }

  sensores[i]->setShunt(
    shuntOhms[i],
    correnteMaxA[i]
  );

  sensores[i]->setAveragingCount(INA228_COUNT_16);

  return true;
}

// leitura de sensores

void lerSensores() {

  for (int i = 0; i < NUM_SENSORES; i++) {

    // verificar se o sensor responde
    if (!verificarI2C(enderecos[i])) {

      dados[i].valido = false;
      dados[i].tensao = 0;
      dados[i].corrente = 0;

      continue;
    }

    // reinicializar apos falha
    if (!dados[i].valido) {

      if (!iniciarINA(i)) {
        dados[i].valido = false;
        dados[i].tensao = 0;
        dados[i].corrente = 0;
        continue;
      }
    }

    dados[i].tensao =
      sensores[i]->readBusVoltage();

    // conversao de mA para A
    dados[i].corrente =
      sensores[i]->getCurrent_mA() / 1000.0f;

    dados[i].valido = true;
  }
}

// envio de dados para a jetson

void enviarDados() {

  Serial2.print("DATA");

  for (int i = 0; i < NUM_SENSORES; i++) {

    Serial2.print(",");
    Serial2.print(dados[i].tensao, 3);

    Serial2.print(",");
    Serial2.print(dados[i].corrente, 3);

    Serial2.print(",");
    Serial2.print(dados[i].valido ? 1 : 0);
  }

  Serial2.println();

  // erros
  for (int i = 0; i < NUM_SENSORES; i++) {

    if (!dados[i].valido) {

      Serial2.print("ERROR,");
      Serial2.print(nomes[i]);
      Serial2.println(",FALHA_I2C");

    } else if (dados[i].tensao < TENSAO_MINIMA) {

      Serial2.print("WARN,");
      Serial2.print(nomes[i]);
      Serial2.println(",SEM_TENSAO");
    }
  }
}

// ========================================
// DEBUG USB
// ========================================

void imprimirDebug() {

  Serial.println("-----------------------");

  for (int i = 0; i < NUM_SENSORES; i++) {

    Serial.print(nomes[i]);
    Serial.print(" | ");

    if (!dados[i].valido) {
      Serial.println("FALHA I2C");
      continue;
    }

    Serial.print(dados[i].tensao, 3);
    Serial.print(" V | ");

    Serial.print(dados[i].corrente, 3);
    Serial.println(" A");

    if (dados[i].tensao < TENSAO_MINIMA) {
      Serial.print("AVISO: Nao chegando tensao para ");
      Serial.println(nomes[i]);
    }
  }
}

void setup() {

  Serial.begin(115200);
  Serial2.begin(
    BAUD_RATE,
    SERIAL_8N1,
    UART_RX,
    UART_TX
  );


  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000);

  delay(500);

  Serial.println("Sistema AVANT iniciado");

  // inicio dos 5 sensores
  for (int i = 0; i < NUM_SENSORES; i++) {

    dados[i].tensao = 0;
    dados[i].corrente = 0;
    dados[i].valido = iniciarINA(i);

    Serial.print(nomes[i]);
    Serial.println(
      dados[i].valido ? " OK" : " ERRO"
    );
  }
}


void loop() {

  unsigned long agora = millis();

  if (agora - ultimaLeitura >= INTERVALO_MS) {

    ultimaLeitura = agora;

    lerSensores();

    enviarDados();

    imprimirDebug();
  }
}
