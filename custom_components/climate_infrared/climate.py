import logging
import asyncio
from datetime import datetime

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    ClimateEntityFeature,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
    FAN_FOCUS,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import async_track_state_change_event, async_call_later

from .const import DEFAULT_MIN_TEMP, DEFAULT_MAX_TEMP

_LOGGER = logging.getLogger(__name__)

_FAN_KEYS = {
    FAN_LOW: "low",
    FAN_MEDIUM: "medium",
    FAN_HIGH: "high",
    FAN_AUTO: "auto",
    FAN_FOCUS: "focus",
}

_MODES_WITH_TEMPERATURE = (HVACMode.COOL, HVACMode.HEAT, HVACMode.AUTO)
_MODES_WITH_FAN = (
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.AUTO,
    HVACMode.FAN_ONLY,
)


class ClimateInfrared(ClimateEntity, RestoreEntity):

    def __init__(self, hass, config):
        self.hass = hass

        self._name = config.get("name")
        self._controller = config.get("controller")
        self._remote = config.get("remote")
        self._sensor_temp = config.get("temp_sensor")
        self._sensor_humidity = config.get("humidity_sensor")
        self._sensor_power = config.get("power_sensor")
        self._min_temp = int(config.get("min_temp", DEFAULT_MIN_TEMP))
        self._max_temp = int(config.get("max_temp", DEFAULT_MAX_TEMP))
        self._standalone_power_on = bool(config.get("standalone_power_on", False))

        self._hvac_mode = HVACMode.OFF
        self._last_hvac_mode = HVACMode.COOL
        self._fan_mode = FAN_AUTO
        self._target_temperature = 24

        # Proteções contra loop
        self._booting = True
        self._updating_from_sensor = False
        self._pending_sync_unsub = None

        self._attr_name = self._name
        self._attr_unique_id = f"climate_ir_{self._name}"
        self._attr_translation_key = "infrared"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

        self._attr_hvac_modes = config.get("hvac_modes", [])
        self._attr_fan_modes = config.get("fan_modes", [])

    # --------------------------------------------------
    # RESTORE + LISTENERS
    # --------------------------------------------------

    async def async_added_to_hass(self):
        last = await self.async_get_last_state()

        if last:
            try:
                self._hvac_mode = HVACMode(last.state)
                self._target_temperature = last.attributes.get("temperature", 24)
                self._fan_mode = last.attributes.get("fan_mode", FAN_AUTO)
            except Exception:
                self._hvac_mode = HVACMode.OFF

            if self._hvac_mode != HVACMode.OFF:
                self._last_hvac_mode = self._hvac_mode
            else:
                saved = last.attributes.get("last_hvac_mode")
                if saved:
                    try:
                        restored = HVACMode(saved)
                        if restored != HVACMode.OFF:
                            self._last_hvac_mode = restored
                    except Exception:
                        pass

        self._target_temperature = int(
            max(self._min_temp, min(self._max_temp, int(self._target_temperature)))
        )

        # Esperar HA estabilizar
        await asyncio.sleep(2)
        self._booting = False

        # --- MONITOR POWER SENSOR ---
        if self._sensor_power:

            async def sensor_changed(event):
                await self._schedule_sensor_sync()

            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._sensor_power],
                    sensor_changed,
                )
            )

            await self._schedule_sensor_sync()

        # --- MONITOR TEMPERATURE SENSOR ---
        if self._sensor_temp:

            async def temp_changed(event):
                self.async_write_ha_state()

            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._sensor_temp],
                    temp_changed,
                )
            )

        # --- MONITOR HUMIDITY SENSOR ---
        if self._sensor_humidity:

            async def humidity_changed(event):
                self.async_write_ha_state()

            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._sensor_humidity],
                    humidity_changed,
                )
            )

    # --------------------------------------------------
    # PROPRIEDADES
    # --------------------------------------------------

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def supported_features(self):
        features = ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        if self._hvac_mode == HVACMode.FAN_ONLY:
            features |= ClimateEntityFeature.FAN_MODE
        elif self._hvac_mode in _MODES_WITH_TEMPERATURE:
            features |= (
                ClimateEntityFeature.TARGET_TEMPERATURE
                | ClimateEntityFeature.FAN_MODE
            )
        return features

    @property
    def extra_state_attributes(self):
        return {
            "last_hvac_mode": self._last_hvac_mode,
        }

    @property
    def fan_mode(self):
        return self._fan_mode

    @property
    def target_temperature(self):
        return self._target_temperature

    @property
    def target_temperature_step(self):
        return 1

    @property
    def min_temp(self):
        return self._min_temp

    @property
    def max_temp(self):
        return self._max_temp

    @property
    def current_temperature(self):
        if not self._sensor_temp:
            return None

        s = self.hass.states.get(self._sensor_temp)
        if s:
            try:
                return float(s.state)
            except Exception:
                return None

    @property
    def current_humidity(self):
        if not self._sensor_humidity:
            return None

        s = self.hass.states.get(self._sensor_humidity)
        if s:
            try:
                return float(s.state)
            except Exception:
                return None

    # --------------------------------------------------
    # DEBOUNCE INTELIGENTE
    # --------------------------------------------------

    async def _schedule_sensor_sync(self):
        if self._booting:
            return

        if self._pending_sync_unsub:
            self._pending_sync_unsub()
            self._pending_sync_unsub = None

        async def _run(_now):
            await self._safe_sensor_sync()

        self._pending_sync_unsub = async_call_later(
            self.hass,
            1.0,
            _run
        )

    async def _safe_sensor_sync(self):
        if self._updating_from_sensor:
            return

        try:
            self._updating_from_sensor = True
            await self._sync_from_sensor()
        finally:
            self._updating_from_sensor = False
            self._pending_sync_unsub = None

    # --------------------------------------------------
    # SINCRONIZAÇÃO APENAS DE ESTADO
    # --------------------------------------------------

    def _resolved_last_hvac_mode(self):
        if (
            self._last_hvac_mode
            and self._last_hvac_mode != HVACMode.OFF
            and self._last_hvac_mode in self._attr_hvac_modes
        ):
            return self._last_hvac_mode
        if HVACMode.COOL in self._attr_hvac_modes:
            return HVACMode.COOL
        for mode in self._attr_hvac_modes:
            if mode != HVACMode.OFF:
                return mode
        return HVACMode.COOL

    async def _sync_from_sensor(self):
        s = self.hass.states.get(self._sensor_power)
        if not s:
            return

        aberto = s.state in ["on", "true", "ligado"]
        modo_atual = self._hvac_mode

        novo = None

        # Sensor FECHOU → refletir como OFF (mantém _last_hvac_mode)
        if modo_atual != HVACMode.OFF and not aberto:
            self._last_hvac_mode = modo_atual
            novo = HVACMode.OFF

        # Sensor ABRIU → restaurar último modo ativo
        elif modo_atual == HVACMode.OFF and aberto:
            novo = self._resolved_last_hvac_mode()

        if novo and novo != self._hvac_mode:
            _LOGGER.info("[%s] Sync sensor → %s", self._name, novo)
            self._hvac_mode = novo
            if novo != HVACMode.OFF:
                self._last_hvac_mode = novo
            self.async_write_ha_state()

    # --------------------------------------------------
    # COMANDOS DO USUÁRIO
    # --------------------------------------------------

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == self._hvac_mode:
            return

        prev_mode = self._hvac_mode
        self._hvac_mode = hvac_mode

        if hvac_mode != HVACMode.OFF:
            self._last_hvac_mode = hvac_mode
        elif prev_mode != HVACMode.OFF:
            self._last_hvac_mode = prev_mode

        if hvac_mode == HVACMode.OFF:
            await self._send("off")
        else:
            if (
                self._standalone_power_on
                and prev_mode == HVACMode.OFF
                and hvac_mode != HVACMode.OFF
            ):
                await self._send("on")
                await asyncio.sleep(1.5)
            await self._send_combined()

        self.async_write_ha_state()

    async def async_turn_on(self):
        if self._hvac_mode != HVACMode.OFF:
            return
        await self.async_set_hvac_mode(self._resolved_last_hvac_mode())

    async def async_turn_off(self):
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs):
        temp = int(kwargs.get("temperature"))
        temp = max(self._min_temp, min(self._max_temp, temp))

        if temp == self._target_temperature:
            return

        self._target_temperature = temp

        if self._uses_temperature():
            await self._send_combined()
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        if fan_mode == self._fan_mode:
            return

        self._fan_mode = fan_mode

        if self._uses_fan():
            await self._send_combined()
        self.async_write_ha_state()

    # --------------------------------------------------
    # MONTAGEM DO COMANDO IR
    # --------------------------------------------------

    def _uses_temperature(self):
        return self._hvac_mode in _MODES_WITH_TEMPERATURE

    def _uses_fan(self):
        return self._hvac_mode in _MODES_WITH_FAN

    def _fan_key(self):
        return _FAN_KEYS.get(self._fan_mode, "auto")

    def _command_key(self):
        if self._hvac_mode == HVACMode.OFF:
            return "off"
        if self._hvac_mode == HVACMode.DRY:
            return "dry"

        fan = self._fan_key()
        if self._hvac_mode == HVACMode.FAN_ONLY:
            return f"fan_only_{fan}"

        mode = self._hvac_mode.value.lower()
        return f"{mode}_{fan}_{int(self._target_temperature)}"

    async def _send_combined(self):
        await self._send(self._command_key())

    # --------------------------------------------------
    # ENVIO REAL PARA CONTROLE IR
    # --------------------------------------------------

    async def _send(self, command):
        _LOGGER.info(
            "[%s] IR -> %s (controller=%s device=%s)",
            self._name,
            command,
            self._controller,
            self._remote,
        )

        await self.hass.services.async_call(
            "remote",
            "send_command",
            {
                "entity_id": self._controller,
                "device": self._remote,
                "command": command,
            },
            blocking=True,
        )


# ------------------------------------------------------
# SETUP
# ------------------------------------------------------

async def async_setup_entry(hass, entry, async_add_entities):
    config = {**entry.data, **entry.options}

    async_add_entities([
        ClimateInfrared(hass, config)
    ])
