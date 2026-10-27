import voluptuous as vol
from voluptuous import UNDEFINED

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.components.climate.const import (
    HVACMode,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
    FAN_FOCUS,
)

from .const import DOMAIN, DEFAULT_MIN_TEMP, DEFAULT_MAX_TEMP

HVAC_MODE_OPTIONS = [
    HVACMode.OFF,
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.DRY,
    HVACMode.FAN_ONLY,
    HVACMode.AUTO,
]

FAN_MODE_OPTIONS = [
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
    FAN_FOCUS,
]

_SENSOR_KEYS = ("temp_sensor", "humidity_sensor", "power_sensor")


def _normalize_config(data):
    normalized = data.copy()
    for key in _SENSOR_KEYS:
        if not normalized.get(key):
            normalized[key] = None
    for key in ("min_temp", "max_temp"):
        if normalized.get(key) is not None:
            normalized[key] = int(normalized[key])
    normalized["swing"] = bool(normalized.get("swing", False))
    return normalized


def _stored(current, key, fallback):
    value = current.get(key, fallback)
    if value in (None, ""):
        return fallback
    return value


def _sensor_default(current, key):
    value = current.get(key)
    if not value:
        return UNDEFINED
    return value


def _options_schema(current):
    return vol.Schema(
        {
            vol.Required(
                "hvac_modes",
                default=_stored(
                    current,
                    "hvac_modes",
                    [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT],
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=HVAC_MODE_OPTIONS,
                    multiple=True,
                    mode="dropdown",
                )
            ),
            vol.Required(
                "fan_modes",
                default=_stored(
                    current,
                    "fan_modes",
                    [FAN_LOW, FAN_MEDIUM, FAN_HIGH],
                ),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=FAN_MODE_OPTIONS,
                    multiple=True,
                    mode="dropdown",
                )
            ),
            vol.Optional(
                "temp_sensor",
                default=_sensor_default(current, "temp_sensor"),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                "humidity_sensor",
                default=_sensor_default(current, "humidity_sensor"),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(
                "power_sensor",
                default=_sensor_default(current, "power_sensor"),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="binary_sensor")
            ),
            vol.Required(
                "min_temp",
                default=int(_stored(current, "min_temp", DEFAULT_MIN_TEMP)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=50,
                    step=1,
                    mode="box",
                )
            ),
            vol.Required(
                "max_temp",
                default=int(_stored(current, "max_temp", DEFAULT_MAX_TEMP)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=50,
                    step=1,
                    mode="box",
                )
            ),
            vol.Required(
                "standalone_power_on",
                default=bool(_stored(current, "standalone_power_on", False)),
            ): selector.BooleanSelector(),
            vol.Required(
                "swing",
                default=bool(_stored(current, "swing", False)),
            ): selector.BooleanSelector(),
        }
    )


class ClimateInfraredConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ClimateInfraredOptionsFlow()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            min_temp = user_input.get("min_temp", DEFAULT_MIN_TEMP)
            max_temp = user_input.get("max_temp", DEFAULT_MAX_TEMP)
            if min_temp > max_temp:
                errors["base"] = "min_temp_gt_max_temp"
            else:
                return self.async_create_entry(
                    title=user_input["name"],
                    data=_normalize_config(user_input),
                )

        schema = vol.Schema(
            {
                vol.Required("name"): str,
                vol.Required("controller"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="remote")
                ),
                vol.Required("remote"): str,
            }
        ).extend(_options_schema({}).schema)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class ClimateInfraredOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        current = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            min_temp = user_input.get("min_temp", DEFAULT_MIN_TEMP)
            max_temp = user_input.get("max_temp", DEFAULT_MAX_TEMP)
            if min_temp > max_temp:
                errors["base"] = "min_temp_gt_max_temp"
            else:
                return self.async_create_entry(
                    title="",
                    data=_normalize_config(user_input),
                )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(current),
            errors=errors,
        )
