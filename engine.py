"""Lógica de evaluación GUIOSAD (sin dependencia de UI)."""

from __future__ import annotations

from dataclasses import dataclass, field

from guiosad import Guiosad


@dataclass
class FactorState:
    decisor_importance: int = 1
    scope: str = "Interno"
    subfactor_values: list[int] = field(default_factory=list)
    global_weight: float | None = None
    foda: str = ""
    evaluated: bool = False


class EvaluationEngine:
    FODA_THRESHOLD = 3

    RECOMMENDATION_A = (
        "Recomendación A: Adoptar. Todos los factores han sido identificados como "
        "Oportunidades y/o Fortalezas. La organización cumple satisfactoriamente con "
        "la mayoría de requisitos para adoptar la solución FLOSS."
    )
    RECOMMENDATION_B = (
        "Recomendación B: Es posible adoptar. Se detectaron amenazas y/o debilidades "
        "en factores cuya importancia relativa es opcional; se sugiere revisar los "
        "criterios que no cumplen con lo mínimo requerido."
    )
    RECOMMENDATION_C = (
        "Recomendación C: La organización debe proporcionar los recursos necesarios "
        "para una adopción satisfactoria. Factores internos: mejorar en la "
        "organización; factores externos: dedicar recursos de ingeniería al software."
    )

    def __init__(self, model: Guiosad | None = None):
        self.model = model or Guiosad()
        self.factor_states: list[FactorState] = []
        self._init_states()

    def _init_states(self) -> None:
        self.factor_states = []
        for factor in self.model.factors:
            scope = factor.scope
            if scope == "Ambos":
                scope = "Interno"
            sub_vals = [1] * len(factor.subfactors)
            self.factor_states.append(
                FactorState(
                    decisor_importance=1,
                    scope=scope,
                    subfactor_values=sub_vals,
                )
            )

    @property
    def factor_names(self) -> list[str]:
        return self.model.factors_lbls

    def suggested_label(self, index: int) -> str:
        imp = self.model.factors[index].suggested_importance
        return Guiosad.levels_lbls[imp - 1]

    def suggested_index(self, index: int) -> int:
        return self.model.factors[index].suggested_importance - 1

    def raw_scope(self, index: int) -> str:
        return self.model.factors[index].scope

    def relative_importance(self, index: int) -> tuple[str, bool]:
        suggested = self.model.factors[index].suggested_importance - 1
        decisor = self.factor_states[index].decisor_importance - 1
        r_idx = (suggested + decisor) // 2
        label = Guiosad.levels_lbls[r_idx]
        relevant = r_idx > 0
        return label, relevant

    def relevant_factor_indices(self) -> list[int]:
        return [i for i in range(len(self.factor_states)) if self.relative_importance(i)[1]]

    def relevant_factor_names(self) -> list[str]:
        return [self.factor_names[i] for i in self.relevant_factor_indices()]

    def save_subfactors(self, index: int, values: list[int]) -> None:
        state = self.factor_states[index]
        state.subfactor_values = values[:]
        if not values:
            return
        state.global_weight = sum(values) / len(values)
        state.evaluated = True
        state.foda = self.compute_foda(state.scope, state.global_weight)

    def compute_foda(self, scope: str, global_weight: float) -> str:
        if scope == "Interno":
            return "Fortaleza" if global_weight >= self.FODA_THRESHOLD else "Debilidad"
        return "Oportunidad" if global_weight >= self.FODA_THRESHOLD else "Amenaza"

    def foda_row_status(self, index: int) -> str:
        _, relevant = self.relative_importance(index)
        state = self.factor_states[index]
        if not relevant:
            return "no_relevant"
        if not state.evaluated:
            return "pending"
        return "done"

    def compute_recommendation(self) -> tuple[str, str]:
        """
        Devuelve (texto_recomendación, estilo: success | warning | error | neutral).
        """
        relative_list: list[str] = []
        foda_list: list[str] = []

        for i, state in enumerate(self.factor_states):
            status = self.foda_row_status(i)
            if status != "done":
                continue
            rel_label, _ = self.relative_importance(i)
            relative_list.append(rel_label)
            foda_list.append(state.foda)

        if not foda_list:
            return "", "neutral"

        good = sum(1 for f in foda_list if f in ("Fortaleza", "Oportunidad"))
        bad = sum(1 for f in foda_list if f in ("Debilidad", "Amenaza"))

        has_critical = False
        has_optional_risk = False
        for rel, foda in zip(relative_list, foda_list):
            if foda in ("Amenaza", "Debilidad") and rel in ("Importante", "Fundamental"):
                has_critical = True
            elif foda in ("Amenaza", "Debilidad") and rel == "Opcional":
                has_optional_risk = True

        if has_critical:
            return self.RECOMMENDATION_C, "error"
        if has_optional_risk:
            return self.RECOMMENDATION_B, "warning"
        if good > bad:
            return self.RECOMMENDATION_A, "success"
        if good < bad:
            return (
                f"No adoptar: {bad} factores como Debilidad/Amenaza frente a "
                f"{good} como Fortaleza/Oportunidad.",
                "error",
            )
        return (
            f"Empate ({good} vs {bad}). Considerar factores no analizados por GUIOSAD.",
            "warning",
        )

    def summary_counts(self) -> dict[str, int]:
        counts = {
            "Fortaleza": 0,
            "Oportunidad": 0,
            "Debilidad": 0,
            "Amenaza": 0,
            "Pendiente": 0,
            "No relevante": 0,
        }
        for i in range(len(self.factor_states)):
            status = self.foda_row_status(i)
            if status == "no_relevant":
                counts["No relevante"] += 1
            elif status == "pending":
                counts["Pendiente"] += 1
            else:
                counts[self.factor_states[i].foda] += 1
        return counts
