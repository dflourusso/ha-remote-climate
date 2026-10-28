# 🌬️ Climate Infrared (IR Climate for Home Assistant)

Integração customizada para controlar **ar-condicionado via infravermelho (IR)** usando o componente `remote` do Home Assistant (Broadlink, ESPHome IR, Zigbee IR, etc).

<img width="850" alt="Screenshot 2026-01-26 at 15 06 21" src="https://github.com/user-attachments/assets/6da28da0-06b9-4770-81f3-c1dece54e213" />

<img width="350" alt="Screenshot 2026-01-26 at 15 04 57" src="https://github.com/user-attachments/assets/d80f0dc4-c308-4491-aeee-988e5f1ccb19" />


Ela simula um `climate` real, com suporte a:
- Modos HVAC (cool, heat, dry, fan_only, auto, off)
- `turn_on` / `turn_off` (restaura o último modo ativo)
- Velocidade do ventilador
- Temperatura alvo
- Sensor externo de temperatura
- Sensor externo de estado (porta, consumo, relay, etc)
- UI completa via Config Flow
- Persistência de estado

---

# ✨ Recursos

- Controle IR por modo (`cool_auto_24`, `heat_low_20`, `fan_only_low`, `dry`)
- Compatível com **Broadlink, ESPHome, Zigbee IR, MQTT IR**
- Sensores externos opcionais:
  - Temperatura real
  - Estado do equipamento (ligado/desligado)
- `climate.turn_on` restaura o último modo HVAC ativo (fallback: cool)
- `climate.turn_off` equivale a `set_hvac_mode(off)`
- Proteção contra loops e storms de eventos
- Debounce inteligente
- Restore state após reboot
- UI Config Flow + Options Flow (editar depois de criado)

---

# 📦 Instalação

## 🔹 Via HACS (recomendado)

1. Adicione este repositório como **Custom Repository** no HACS: `https://github.com/SEU_USUARIO/climate_infrared`
2. Categoria: **Integration**
3. Instale **Climate Infrared**
4. Reinicie o Home Assistant

---

## 🔹 Instalação manual

1. Copie a pasta `custom_components/climate_infrared` para: `/config/custom_components/climate_infrared`
2. Reinicie o Home Assistant

---

# ⚙️ Configuração

Após instalar:

1. Vá em **Configurações → Dispositivos e Serviços → Adicionar Integração**
2. Procure por **Climate Infrared**
3. Preencha os campos:

### Campos obrigatórios

| Campo | Descrição |
|--------|-----------|
| Name | Nome do climate |
| Controller | Entidade `remote.*` (Broadlink, ESPHome, etc) |
| Remote | Nome do dispositivo configurado no remote |
| HVAC Modes | Modos suportados |
| Fan Modes | Velocidades suportadas |

### Campos opcionais

| Campo | Descrição |
|--------|-----------|
| Temp Sensor | Sensor de temperatura real |
| Power Sensor | Sensor que indica se o ar está ligado (porta, consumo, relay, etc) |
| Min Temp | Temperatura mínima permitida (limita o slider e os comandos enviados) |
| Max Temp | Temperatura máxima permitida (limita o slider e os comandos enviados) |
| Standalone Power On | Alguns LG precisam de um comando `on` separado antes de mudar modo/temperatura/ventilador |

---

# 🧠 Padrão de Comandos IR

O comando depende do modo. Temperatura e velocidade continuam guardadas mesmo quando o modo atual não as envia. Ao voltar para frio, quente ou auto, o IR usa esses valores de novo.

| Modo | Comando |
|------|---------|
| off | `off` |
| cool, heat, auto | `{modo}_{velocidade}_{temperatura}` |
| fan_only | `fan_only_{velocidade}` |
| dry | `dry` |

Exemplos:
```
cool_auto_24
cool_low_23
heat_high_26
fan_only_medium
dry
off
```

No card, a temperatura aparece em frio, quente, auto e desligado. A velocidade aparece nesses modos, em `fan_only` e desligado. Em `dry` os dois ficam ocultos.

Mudar a temperatura em `fan_only`, `dry` ou `off` só atualiza o valor guardado. Mudar a velocidade em `dry` ou `off` faz o mesmo. O infravermelho sai na hora quando o campo vale para o modo atual.

Códigos para gravar no remote: o mapa completo de frio, quente e auto; uma chave `fan_only_` por velocidade usada; uma chave `dry`.

O swing das aletas é um comando separado, só ligado ou desligado. Ele não entra em `cool_auto_24` nem nos outros modos. Com o campo de oscilar ligado na configuração, a lista fica visível também com o ar desligado. Nesse estado a escolha só fica guardada. Ligar o ar não reenvia o swing. A janela de detalhes mostra Ligado e Desligado:

```
swing_on
swing_off
```

👉 Cada chave precisa existir no seu `remote` (Broadlink, ESPHome, QA, etc).

---

# 🌡️ Sensores Externos (Opcional)

## Sensor de temperatura

Se configurado, o climate exibirá temperatura real:

```yaml
sensor:
  - platform: mqtt
    name: Sala Temperatura
```

## Sensor de estado (Power Sensor)

Serve apenas para refletir estado, não bloqueia comandos.

Exemplos suportados:

- binary_sensor de porta
- sensor de consumo
- relay smart plug
- sensor custom

Estados considerados ligado:

```
on
true
ligado
```

🔁 Comportamento do Power Sensor

| Sensor | Climate Mode |
|--------|--------------|
| OFF → ON | restaura o último modo ativo (fallback: cool) |
| ON → OFF | muda para OFF |

👉 Não envia IR automaticamente (apenas reflete estado).

# 🔌 turn_on / turn_off

| Serviço | Comportamento |
|---------|---------------|
| `climate.turn_off` | `set_hvac_mode(off)` — envia IR `off` |
| `climate.turn_on` | restaura o último modo HVAC ativo; se não houver histórico válido, usa `cool` |

O último modo ativo também é persistido entre reboots (atributo `last_hvac_mode`).

# 🛠️ Edição de Configuração

Após criado:

- Vá em Configurações → Dispositivos e Serviços
- Clique na integração
- Clique em Configurar

Você pode editar:
- HVAC modes, inclusive `dry` e `fan_only`
- Fan modes
- Sensores
- Temperatura mínima e máxima
- Comando de ligar separado
- Oscilar aletas

Nome, controle IR e nome do dispositivo ficam como foram definidos na criação.

# 🧩 Compatibilidade

Testado com:

- Broadlink RM4 / RM Mini
- HA Remote Quereo Automação

> Deve funcionar com qualquer IR entity suportado no Home Assistant.

# ⚠️ Limitações Conhecidas

- Não aprende códigos IR (use Broadlink/ESPHome)
- Não detecta temperatura alvo real do AC (IR é unidirecional)
- Power sensor é apenas heurístico


# 👨‍💻 Autor

Daniel Lourusso
Projeto pessoal para automação residencial avançada.
