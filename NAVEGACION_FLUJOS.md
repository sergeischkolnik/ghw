# Mapa de Navegación de Flujos - Bot de Workflow

## FLUJO TALLER

### Secuencia Esperada:
```
TYPE_CHOICE → MACHINE_NAME → MACHINE_NUM → COMPONENT → SUBCOMPONENT → CHECKLIST → COMMENT_CHOICE → COMMENT_TEXT/PANAS_CHOICE → PANAS_CHOICE → PANAS_TEXT/FINISH
```

### Verificación de Botones Atrás:

| Desde | Botón Atrás Enviado | Debe ir a | ✅ Correcto |
|-------|---------------------|-----------|-----------|
| MACHINE_NAME | `back\|TYPE_CHOICE` | TYPE_CHOICE | ✅ |
| MACHINE_NUM | `back\|MACHINE_NAME` | MACHINE_NAME | ✅ |
| COMPONENT | `back\|MACHINE_NUM` | MACHINE_NUM | ✅ |
| SUBCOMPONENT | `back\|COMPONENT` | COMPONENT | ✅ |
| CHECKLIST | `back\|SUBCOMPONENT` | SUBCOMPONENT | ✅ |
| COMMENT_CHOICE | `back\|CHECKLIST` | CHECKLIST | ✅ |
| COMMENT_TEXT | `back\|COMMENT_CHOICE` | COMMENT_CHOICE | ✅ |
| PANAS_CHOICE | `back\|COMMENT_CHOICE` | COMMENT_CHOICE | ✅ |
| PANAS_TEXT | `back\|PANAS_CHOICE` | PANAS_CHOICE | ✅ |

---

## FLUJO SERVICIO

### Secuencia Esperada (Con Podadora/Detalles):
```
TYPE_CHOICE → SERVICE_CLIENT_SEARCH → SERVICE_CLIENT_SELECT → SERVICE_SERVICE_SELECT 
→ SERVICE_SUBSERVICE_SELECT → SERVICE_DETAIL_HILERAS → SERVICE_DETAIL_CARAS → SERVICE_DETAIL_PASADAS 
→ SERVICE_HOROMETRO_INICIO → SERVICE_HOROMETRO_TERMINO → SERVICE_HECTAREAS 
→ COMMENT_CHOICE → COMMENT_TEXT/PANAS_CHOICE → PANAS_CHOICE → PANAS_TEXT/FINISH
```

### Secuencia Esperada (Sin Detalles - COSECHA/BARREDORA):
```
TYPE_CHOICE → SERVICE_CLIENT_SEARCH → SERVICE_CLIENT_SELECT → SERVICE_SERVICE_SELECT 
→ SERVICE_HOROMETRO_INICIO → SERVICE_HOROMETRO_TERMINO → SERVICE_HECTAREAS 
→ COMMENT_CHOICE → COMMENT_TEXT/PANAS_CHOICE → PANAS_CHOICE → PANAS_TEXT/FINISH
```

### Verificación de Botones Atrás - Búsqueda de Cliente:

| Desde | Botón Atrás Enviado | Debe ir a | ✅ Correcto |
|-------|---------------------|-----------|-----------|
| SERVICE_CLIENT_SEARCH (búsqueda) | `back\|TYPE_CHOICE` | TYPE_CHOICE | ✅ |
| SERVICE_CLIENT_SELECT (selección) | `back\|SERVICE_CLIENT_SEARCH` | SERVICE_CLIENT_SEARCH | ✅ |

### Verificación de Botones Atrás - Selección Servicio:

| Desde | Botón Atrás Enviado | Debe ir a | ✅ Correcto |
|-------|---------------------|-----------|-----------|
| SERVICE_SERVICE_SELECT | `back\|SERVICE_CLIENT_SELECT` | SERVICE_CLIENT_SELECT | ✅ |
| SERVICE_SUBSERVICE_SELECT | `back\|SERVICE_SERVICE_SELECT` | SERVICE_SERVICE_SELECT | ✅ |

### Verificación de Botones Atrás - Detalles (Podadora):

| Desde | Botón Atrás Enviado | Debe ir a | ✅ Correcto |
|-------|---------------------|-----------|-----------|
| SERVICE_DETAIL_HILERAS | `back\|SERVICE_DETAIL_HILERAS` | SERVICE_DETAIL_HILERAS | ⚠️ LOOP - Debería ser SERVICE_SUBSERVICE_SELECT |
| SERVICE_DETAIL_CARAS | `back\|SERVICE_DETAIL_CARAS` | SERVICE_DETAIL_CARAS | ⚠️ LOOP - Debería ser SERVICE_DETAIL_HILERAS |
| SERVICE_DETAIL_PASADAS | `back\|SERVICE_DETAIL_PASADAS` | SERVICE_DETAIL_PASADAS | ⚠️ LOOP - Debería ser SERVICE_DETAIL_CARAS |

**⚠️ PROBLEMA DETECTADO:** Los botones atrás en detalles crean loops infinitos. El handler está bien estructurado, pero los botones enviados son incorrectos.

### Verificación de Botones Atrás - Texto Libre (Horómetro/Hectáreas):

| Desde | Botón Atrás Enviado | Debe ir a | Estado Esperado | ✅ Correcto |
|-------|---------------------|-----------|-----------------|-----------|
| SERVICE_HOROMETRO_INICIO (mensaje) | `back\|SERVICE_HOROMETRO_INICIO` | Depende de detalles | CALLBACK QUERY - ERROR ⚠️ | ❌ |
| SERVICE_HOROMETRO_TERMINO (mensaje) | `back\|SERVICE_HOROMETRO_TERMINO` | SERVICE_HOROMETRO_INICIO | CALLBACK QUERY - ERRO ⚠️ | ❌ |
| SERVICE_HECTAREAS (mensaje) | `back\|SERVICE_HECTAREAS` | SERVICE_HOROMETRO_TERMINO | CALLBACK QUERY - ERROR ⚠️ | ❌ |
| COMMENT_CHOICE (desde hectáreas) | `back\|COMMENT_CHOICE` | SERVICE_HECTAREAS | ✅ | ✅ |

**⚠️ PROBLEMA DETECTADO:** Los campos de texto libre envían botones atrás como callbacks, pero MessageHandler no puede procesar callbacks. El usuario necesita escribir texto, no presionar botones.

---

## PROBLEMAS IDENTIFICADOS

### 1. **Loops en Detalles (SERVICE_DETAIL_*)**
- **Línea 725:** SERVICE_DETAIL_HILERAS envía `back|SERVICE_DETAIL_HILERAS` (debe ser `back|SERVICE_SUBSERVICE_SELECT`)
- **Línea 756:** SERVICE_DETAIL_CARAS envía `back|SERVICE_DETAIL_CARAS` (debe ser `back|SERVICE_DETAIL_HILERAS`)
- **Línea 789:** SERVICE_DETAIL_PASADAS envía `back|SERVICE_DETAIL_PASADAS` (debe ser `back|SERVICE_DETAIL_CARAS`)

### 2. **Campos de Texto Libre con Botones Atrás Inválidos**
- **Línea 813, 1051, 1065, 1074:** Envían botones atrás a MessageHandler (debería aceptar texto)
- Los usuarios no pueden presionar "Atrás" en campos de texto libre via callback

### 3. **COMMENT_CHOICE desde Héctareas**
- Necesita identificar si viene del flujo TALLER o SERVICIO
- Línea 1227: Intenta distinguir pero usa `context.user_data['workflow'].get('hectareas')`

---

## RECOMENDACIONES DE CORRECCIÓN

1. **Arreglar loops en detalles:** Actualizar callback_data en show_service_detail_*
2. **Arreglar campos de texto:** Permitir navegación atrás editorial en campos de texto (requiere cambio de arquitectura con botones inline antes del campo)
3. **Validar COMMENT_CHOICE:** Asegurar que distingue correctamente entre TALLER y SERVICIO

