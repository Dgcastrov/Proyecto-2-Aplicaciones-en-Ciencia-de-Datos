
import pandas as pd
import matplotlib.pyplot as plt
import os


ruta = "Data/Raw"

archivos = {
    "asequibilidad": "share-healthy-diet-unaffordable.csv",
    "personas": "number-healthy-diet-unaffordable.csv",
    "costo": "cost-healthy-diet.csv",
    "pobreza": "share-living-with-less-than-upper-middle-income-poverty-line.csv",
    "alimentos": "cost-foods-healthy-diet.csv"
}

datos = {}

for nombre, archivo in archivos.items():
    datos[nombre] = pd.read_csv(os.path.join(ruta, archivo))

    print("\nDATASET:", nombre)
    print("Filas:", len(datos[nombre]))
    print("Columnas:", list(datos[nombre].columns))
    print("Años:", datos[nombre]["Year"].min(),
          "-", datos[nombre]["Year"].max())
    print("Valores faltantes:")
    print(datos[nombre].isna().sum())

paises = {          #se selecciono america latina
    "ARG": "Argentina",
    "BOL": "Bolivia",
    "BRA": "Brasil",
    "CHL": "Chile",
    "COL": "Colombia",
    "CRI": "Costa Rica",
    "CUB": "Cuba",
    "DOM": "República Dominicana",
    "ECU": "Ecuador",
    "SLV": "El Salvador",
    "GTM": "Guatemala",
    "HTI": "Haití",
    "HND": "Honduras",
    "MEX": "México",
    "NIC": "Nicaragua",
    "PAN": "Panamá",
    "PRY": "Paraguay",
    "PER": "Perú",
    "URY": "Uruguay",
    "VEN": "Venezuela"
}

#delimitar los pauses
for nombre in datos:
    datos[nombre] = datos[nombre][datos[nombre]["Code"].isin(paises.keys())].copy()
    datos[nombre] = datos[nombre][datos[nombre]["Year"].between(2017, 2024)].copy()


# ==========================================
# 3. COMPROBAR DUPLICADOS
# ==========================================

print("\nDuplicados")

for nombre, df in datos.items():

    duplicados = df.duplicated(subset=["Code", "Year"]).sum()

    print(nombre, ":", duplicados, "duplicados")

    if duplicados > 0:
        raise ValueError(
            "Hay claves país-año duplicadas en " + nombre
        )


# ==========================================
# 4. MATRIZ DE DISPONIBILIDAD
# ==========================================

print("\n===== DISPONIBILIDAD DE DATOS =====")

disponibilidad = []

for codigo, pais in paises.items():

    fila = {
        "Pais": pais,
        "Code": codigo
    }

    for nombre, df in datos.items():

        registros = df[df["Code"] == codigo]

        # Número de años con datos para todas
        # las variables del archivo
        columnas_valor = [
            c for c in df.columns
            if c not in ["Entity", "Code", "Year"]
        ]

        registros = registros.dropna(
            subset=columnas_valor
        )

        fila[nombre] = registros["Year"].nunique()

    disponibilidad.append(fila)

cobertura = pd.DataFrame(disponibilidad)

print(
    cobertura.to_string(index=False)
)


# ==========================================
# 5. PREPARAR LAS VARIABLES
# ==========================================

asequibilidad = datos["asequibilidad"].rename(
    columns={
        "Share of the population who cannot afford a healthy diet":
        "porcentaje_sin_acceso"
    }
)

personas = datos["personas"].rename(
    columns={
        "Number of people who cannot afford a healthy diet":
        "personas_afectadas"
    }
)

costo = datos["costo"].rename(
    columns={
        "Cost of a healthy diet":
        "costo_dieta"
    }
)

pobreza = datos["pobreza"].rename(
    columns={
        "Share of population in poverty ($8.30 a day)":
        "porcentaje_pobreza"
    }
)

# ==========================================
# 6. INTEGRAR LAS BASES
# ==========================================

# Conservamos todos los registros de
# asequibilidad y agregamos las demás variables.

base = asequibilidad[
    ["Entity", "Code", "Year", "porcentaje_sin_acceso"]
].copy()

fuentes = [
    (personas, "personas_afectadas"),
    (costo, "costo_dieta"),
    (pobreza, "porcentaje_pobreza")
]

for df, variable in fuentes:

    antes = len(base)

    base = base.merge(
        df[["Code", "Year", variable]],
        on=["Code", "Year"],
        how="left",
        validate="one_to_one",
        indicator=True
    )

    print("\nIntegración:", variable)
    print("Filas antes:", antes)
    print("Filas después:", len(base))
    print("Sin correspondencia:",
          (base["_merge"] == "left_only").sum())

    base = base.drop(columns=["_merge"])

# No rellenamos años ausentes con ceros.
# Cero y dato faltante significan cosas distintas.

print("\n===== BASE INTEGRADA =====")
print(base.head())
print("\nValores faltantes:")
print(base.isna().sum())


# ==========================================
# 7. ENCONTRAR AÑOS COMUNES
# ==========================================

variables = [
    "porcentaje_sin_acceso",
    "porcentaje_pobreza",
    "costo_dieta"
]

base_completa = base.dropna(
    subset=variables
).copy()

resumen_cobertura = (
    base_completa
    .groupby(["Code", "Entity"])["Year"]
    .nunique()
    .reset_index(name="anios_comunes")
)

# Agregar países sin coincidencias
todos = pd.DataFrame({
    "Code": list(paises.keys()),
    "Pais": list(paises.values())
})

resumen_cobertura = todos.merge(
    resumen_cobertura[["Code", "anios_comunes"]],
    on="Code",
    how="left"
)

resumen_cobertura["anios_comunes"] = (
    resumen_cobertura["anios_comunes"]
    .fillna(0)
    .astype(int)
)

resumen_cobertura = resumen_cobertura.sort_values(
    "anios_comunes", ascending=False
)

print("\n===== AÑOS CON LAS 3 VARIABLES =====")
print(resumen_cobertura.to_string(index=False))


# ==========================================
# 8. DEFINIR PAÍSES ELEGIBLES
# ==========================================

# Criterio metodológico inicial:
# - Al menos 6 de los 8 años comunes
# - Datos comparables en 2017 y 2024
#
# Se fija antes de examinar qué países
# mejoraron o empeoraron.

candidatos = resumen_cobertura[
    resumen_cobertura["anios_comunes"] >= 6
]["Code"].tolist()

inicio = set(
    base_completa[
        base_completa["Year"] == 2017
    ]["Code"]
)

final = set(
    base_completa[
        base_completa["Year"] == 2024
    ]["Code"]
)

candidatos = [
    codigo for codigo in candidatos
    if codigo in inicio and codigo in final
]

print("\n===== PAÍSES ELEGIBLES =====")

for codigo in candidatos:
    print(paises[codigo])


# ==========================================
# 9. COMPARAR 2017 VS 2024
# ==========================================

seleccion = base_completa[
    base_completa["Code"].isin(candidatos)
].copy()

datos_2017 = seleccion[
    seleccion["Year"] == 2017
].set_index("Code")

datos_2024 = seleccion[
    seleccion["Year"] == 2024
].set_index("Code")

comparacion = pd.DataFrame(index=candidatos)

comparacion["Pais"] = [
    paises[codigo] for codigo in candidatos
]

for variable in variables:

    comparacion[variable + "_2017"] = (
        datos_2017[variable]
    )

    comparacion[variable + "_2024"] = (
        datos_2024[variable]
    )

    comparacion["cambio_" + variable] = (
        comparacion[variable + "_2024"]
        - comparacion[variable + "_2017"]
    )

comparacion = comparacion.reset_index(
    names="Code"
)

comparacion = comparacion.sort_values(
    "cambio_porcentaje_sin_acceso",
    ascending=False
)

print("\n===== CAMBIOS 2017-2024 =====")

columnas = [
    "Pais",
    "porcentaje_sin_acceso_2017",
    "porcentaje_sin_acceso_2024",
    "cambio_porcentaje_sin_acceso",
    "porcentaje_pobreza_2024",
    "costo_dieta_2024"
]

print(
    comparacion[columnas]
    .round(2)
    .to_string(index=False)
)


# ==========================================
# 10. IDENTIFICAR TRAYECTORIAS
# ==========================================

# Cambio positivo: empeora la asequibilidad.
# Cambio negativo: mejora.
# Cambio cero: sin variación entre extremos.

def clasificar(cambio):

    if cambio > 0:
        return "Deterioro"
    elif cambio < 0:
        return "Mejora"
    else:
        return "Sin cambio neto"


comparacion["trayectoria"] = (
    comparacion["cambio_porcentaje_sin_acceso"]
    .apply(clasificar)
)

print("\n===== CLASIFICACIÓN =====")

print(
    comparacion[
        ["Pais", "trayectoria",
         "cambio_porcentaje_sin_acceso"]
    ].to_string(index=False)
)


# ==========================================
# 11. GRÁFICA: EVOLUCIÓN TEMPORAL
# ==========================================

plt.figure(figsize=(11, 6))

for codigo in candidatos:

    pais = base[
        base["Code"] == codigo
    ].sort_values("Year")

    plt.plot(
        pais["Year"],
        pais["porcentaje_sin_acceso"],
        marker="o",
        label=paises[codigo]
    )

plt.title(
    "Evolución de la dificultad para costear una dieta saludable"
)
plt.xlabel("Año")
plt.ylabel("Población afectada (%)")
plt.xticks(range(2017, 2025))
plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()


# ==========================================
# 12. GRÁFICA: CAMBIO EN ASEQUIBILIDAD
# ==========================================

orden = comparacion.sort_values(
    "cambio_porcentaje_sin_acceso"
)

plt.figure(figsize=(10, 6))

plt.barh(
    orden["Pais"],
    orden["cambio_porcentaje_sin_acceso"]
)

plt.axvline(0, color="black")

plt.title("Cambio entre 2017 y 2024")
plt.xlabel("Cambio en puntos porcentuales")
plt.tight_layout()
plt.show()


# ==========================================
# 13. GRÁFICA: POBREZA VS ASEQUIBILIDAD
# ==========================================

actual = seleccion[
    seleccion["Year"] == 2024
]

plt.figure(figsize=(10, 6))

plt.scatter(
    actual["porcentaje_pobreza"],
    actual["porcentaje_sin_acceso"],
    s=80
)

for _, fila in actual.iterrows():

    plt.annotate(
        fila["Entity"],
        (
            fila["porcentaje_pobreza"],
            fila["porcentaje_sin_acceso"]
        ),
        xytext=(5, 5),
        textcoords="offset points",
        fontsize=8
    )

plt.xlabel("Población en pobreza (%)")
plt.ylabel("Sin acceso económico a dieta saludable (%)")
plt.title("Pobreza y asequibilidad en 2024")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()


plt.figure(figsize=(10, 6))

plt.scatter(
    actual["costo_dieta"],
    actual["porcentaje_sin_acceso"],
    s=80
)

for _, fila in actual.iterrows():

    plt.annotate(
        fila["Entity"],
        (
            fila["costo_dieta"],
            fila["porcentaje_sin_acceso"]
        ),
        xytext=(5, 5),
        textcoords="offset points",
        fontsize=8
    )

plt.xlabel("Costo diario estimado de dieta saludable")
plt.ylabel("Población afectada (%)")
plt.title("Costo de dieta y asequibilidad en 2024")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()


pares = []

actual = actual.reset_index(drop=True)

for i in range(len(actual)):

    for j in range(i + 1, len(actual)):

        a = actual.iloc[i]
        b = actual.iloc[j]

        diferencia_pobreza = abs(
            a["porcentaje_pobreza"]
            - b["porcentaje_pobreza"]
        )

        diferencia_asequibilidad = abs(
            a["porcentaje_sin_acceso"]
            - b["porcentaje_sin_acceso"]
        )

        if (diferencia_pobreza <= 5 and
                diferencia_asequibilidad >= 10):

            pares.append({
                "Pais_1": a["Entity"],
                "Pais_2": b["Entity"],
                "Diferencia_pobreza_pp": diferencia_pobreza,
                "Diferencia_asequibilidad_pp":
                    diferencia_asequibilidad
            })

pares_df = pd.DataFrame(pares)

print("\n===== PARES INTERESANTES =====")

if len(pares_df) > 0:

    pares_df = pares_df.sort_values(
        "Diferencia_asequibilidad_pp",
        ascending=False
    )

    print(
        pares_df.round(2).to_string(index=False)
    )

else:
    print(
        "No se encontraron pares con estos criterios."
    )


# ==========================================
# 16. GUARDAR LOS RESULTADOS
# ==========================================

os.makedirs("resultados", exist_ok=True)

cobertura.to_csv(
    "resultados/disponibilidad.csv",
    index=False
)

resumen_cobertura.to_csv(
    "resultados/cobertura_integrada.csv",
    index=False
)

base.to_csv(
    "resultados/base_integrada.csv",
    index=False
)

comparacion.to_csv(
    "resultados/comparacion_paises.csv",
    index=False
)

pares_df.to_csv(
    "resultados/pares_interesantes.csv",
    index=False
)

print("\nAnálisis terminado.")
print("Resultados guardados en la carpeta resultados.")
