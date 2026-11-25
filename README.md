# Detective del Museo (Prolog)

Juego de investigación en Prolog. La *Copa de Oro* desaparece de la sala de trofeos a las 8:00 p. m. Tú eres el detective: revisas la escena, interrogas a los sospechosos, comparas sus versiones y acusas al culpable.

**Autor:** Gonzalo Javier Niño Amaris
**Materia:** [nombre de la materia] · Universidad de Pamplona

## Cómo ejecutarlo
1. Instala [SWI-Prolog](https://www.swi-prolog.org/).
2. En la terminal:
```
cd src
swipl juego.pl
?- jugar.
```

## Cómo se juega
| Opción | Qué hace |
|---|---|
| 1 | Revisar la escena del robo |
| 2 | Interrogar a un sospechoso |
| 3 | Ver el cuaderno de pistas |
| 4 | Ver el mapa del museo |
| 5 | Acusar al culpable |
| 6 | Analizar la huella |

Sospechosos: director, guardia, restauradora, guia, donante, conserje (se escriben sin tilde).

## Estructura
- `src/hechos.pl`: base de conocimiento (personas, ubicaciones, coartadas, pistas).
- `src/reglas.pl`: 22 reglas de deducción y el puntaje de sospecha.
- `src/juego.pl`: interfaz del juego (menú, interrogatorios, cuaderno, acusación).

## Reglas principales
`estuvo_en_escena`, `tenia_acceso`, `sin_coartada`, `coartada_falsa`, `tenia_motivo`, `mintio`, `tenia_oportunidad`, `tenia_medios`, `complice`, `descartado`, `puntaje_sospecha`, `sospechoso_principal` y `culpable`.

Una persona es **culpable** si tenía motivo, medios y oportunidad.