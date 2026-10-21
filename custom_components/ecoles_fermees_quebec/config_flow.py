"""Config flow for selecting one or more Quebec schools."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .api import School, TvaApiError, async_fetch_schools, search_schools
from .const import (
    CONF_SCHOOL_ID,
    CONF_SCHOOL_NAME,
    CONF_SEARCH,
    CONF_TOWN,
    DOMAIN,
    MAX_SEARCH_RESULTS,
    MIN_SEARCH_LENGTH,
    SCHOOL_LIST_CACHE_SECONDS,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SEARCH): TextSelector(),
    }
)


class EcolesFermeesQuebecConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Écoles fermées Québec."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._matches: list[School] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a school name or city, then show matching schools."""
        errors: dict[str, str] = {}

        if user_input is not None:
            query = str(user_input.get(CONF_SEARCH) or "").strip()
            if len(query) < MIN_SEARCH_LENGTH:
                errors[CONF_SEARCH] = "search_too_short"
            else:
                try:
                    schools = await self._async_schools()
                except TvaApiError:
                    errors["base"] = "cannot_connect"
                else:
                    configured = self._configured_school_ids()
                    matches = [
                        school
                        for school in search_schools(schools, query)
                        if school.school_id not in configured
                    ]
                    if not matches:
                        errors[CONF_SEARCH] = (
                            "already_configured"
                            if any(
                                school.school_id in configured
                                for school in search_schools(schools, query)
                            )
                            else "no_schools"
                        )
                    elif len(matches) > MAX_SEARCH_RESULTS:
                        errors[CONF_SEARCH] = "too_many_matches"
                    else:
                        self._matches = matches
                        return await self.async_step_school()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_school(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick one matching school."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                school_id = int(user_input[CONF_SCHOOL_ID])
            except (KeyError, TypeError, ValueError):
                errors[CONF_SCHOOL_ID] = "invalid_school"
            else:
                school = next(
                    (item for item in self._matches if item.school_id == school_id),
                    None,
                )
                if school is None:
                    errors[CONF_SCHOOL_ID] = "invalid_school"
                else:
                    await self.async_set_unique_id(str(school.school_id))
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=school.label,
                        data={
                            CONF_SCHOOL_ID: school.school_id,
                            CONF_SCHOOL_NAME: school.name,
                            CONF_TOWN: school.town,
                        },
                    )

        options = [
            SelectOptionDict(value=str(school.school_id), label=school.label)
            for school in sorted(self._matches, key=lambda item: item.label.casefold())
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_SCHOOL_ID): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="school",
            data_schema=schema,
            errors=errors,
            description_placeholders={"count": str(len(self._matches))},
        )

    def _configured_school_ids(self) -> set[int]:
        """Return school IDs already added to Home Assistant."""
        ids: set[int] = set()
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            raw = entry.data.get(CONF_SCHOOL_ID)
            if raw is not None:
                ids.add(int(raw))
        return ids

    async def _async_schools(self) -> list[School]:
        """Fetch the school directory, using a short-lived in-memory cache."""
        domain_data = self.hass.data.setdefault(DOMAIN, {})
        cache = domain_data.get("schools_cache")
        now = self.hass.loop.time()
        if (
            isinstance(cache, dict)
            and cache.get("schools")
            and cache.get("expires", 0) > now
        ):
            return cache["schools"]

        schools = await async_fetch_schools(async_get_clientsession(self.hass))
        domain_data["schools_cache"] = {
            "schools": schools,
            "expires": now + SCHOOL_LIST_CACHE_SECONDS,
        }
        return schools
