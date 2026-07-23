import voluptuous as vol
from voluptuous import UNDEFINED

from homeassistant import config_entries
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


class ClimateInfraredConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            min_temp = user_input.get("min_temp", DEFAULT_MIN_TEMP)
            max_temp = user_input.get("max_temp", DEFAULT_MAX_TEMP)
            if min_temp > max_temp:
                errors["base"] = "min_temp_gt_max_temp"
            else:
                data = user_input.copy()

                # Normalize optional sensors
                for k in ("temp_sensor", "humidity_sensor", "power_sensor"):
                    if not data.get(k):
                        data[k] = None

                return self.async_create_entry(
                    title=data["name"],
                    data=data,
                )

        schema = vol.Schema(
            {
                vol.Required("name"): str,

                vol.Required("controller"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="remote")
                ),

                vol.Required("remote"): str,

                vol.Required(
                    "hvac_modes",
                    default=[HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            HVACMode.OFF,
                            HVACMode.COOL,
                            HVACMode.HEAT,
                            HVACMode.DRY,
                            HVACMode.FAN_ONLY,
                            HVACMode.AUTO,
                        ],
                        multiple=True,
                        mode="dropdown",
                    )
                ),

                vol.Required(
                    "fan_modes",
                    default=[FAN_LOW, FAN_MEDIUM, FAN_HIGH],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            FAN_LOW,
                            FAN_MEDIUM,
                            FAN_HIGH,
                            FAN_AUTO,
                            FAN_FOCUS,
                        ],
                        multiple=True,
                        mode="dropdown",
                    )
                ),

                # Optional sensors
                vol.Optional(
                    "temp_sensor",
                    default=UNDEFINED,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),

                vol.Optional(
                    "humidity_sensor",
                    default=UNDEFINED,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),

                vol.Optional(
                    "power_sensor",
                    default=UNDEFINED,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),

                vol.Optional(
                    "min_temp",
                    default=DEFAULT_MIN_TEMP,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=50,
                        step=1,
                        mode="box",
                    )
                ),

                vol.Optional(
                    "max_temp",
                    default=DEFAULT_MAX_TEMP,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=50,
                        step=1,
                        mode="box",
                    )
                ),

                vol.Optional(
                    "standalone_power_on",
                    default=False,
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
