# 🗺️ Mapa de Navegación Completo - Bot Workflow

**Última actualización:** 12 Mar 2026  
**Estados totales:** 20  
**Flujos:** TALLER + SERVICIO  

---

## 📋 Índice de Estados

| # | Estado | Tipo | Flujo | Línea |
|---|--------|------|-------|-------|
| 0 | `TYPE_CHOICE` | Selección | Ambos | 11 |
| 1 | `MACHINE_NAME` | Selección | TALLER | 11 |
| 2 | `MACHINE_NUM` | Selección | TALLER | 11 |
| 3 | `COMPONENT` | Selección | TALLER | 11 |
| 4 | `SUBCOMPONENT` | Selección | TALLER | 11 |
| 5 | `CHECKLIST` | Multi-select | TALLER | 11 |
| 6 | `COMMENT_CHOICE` | Decisión | TALLER/SERVICIO | 11 |
| 7 | `COMMENT_TEXT` | Entrada texto | TALLER/SERVICIO | 11 |
| 8 | `PANAS_CHOICE` | Decisión | TALLER/SERVICIO | 11 |
| 9 | `PANAS_TEXT` | Entrada texto | TALLER/SERVICIO | 11 |
| 10 | `SERVICE_CLIENT_SEARCH` | Entrada texto | SERVICIO | 11 |
| 11 | `SERVICE_CLIENT_SELECT` | Selección + Paginación | SERVICIO | 11 |
| 12 | `SERVICE_SERVICE_SELECT` | Selección | SERVICIO | 11 |
| 13 | `SERVICE_SUBSERVICE_SELECT` | Selección | SERVICIO | 11 |
| 14 | `SERVICE_DETAIL_HILERAS` | Selección | SERVICIO (PODA/Podadora) | 11 |
| 15 | `SERVICE_DETAIL_CARAS` | Selección | SERVICIO (PODA/Podadora) | 11 |
| 16 | `SERVICE_DETAIL_PASADAS` | Selección | SERVICIO (PODA/Podadora) | 11 |
| 17 | `SERVICE_HOROMETRO_INICIO` | Entrada texto | SERVICIO | 11 |
| 18 | `SERVICE_HOROMETRO_TERMINO` | Entrada texto | SERVICIO | 11 |
| 19 | `SERVICE_HECTAREAS` | Entrada texto | SERVICIO | 11 |

---

## 🔧 FLUJO TALLER - Máquinas y Checklists

### Secuencia Esperada:
```
TYPE_CHOICE 
  ↓ (selecciona TALLER)
MACHINE_NAME 
  ↓
MACHINE_NUM 
  ↓
COMPONENT 
  ↓
SUBCOMPONENT (opcional si component tiene subs)
  ↓
CHECKLIST (multi-select)
  ↓
COMMENT_CHOICE (¿comentarios?)
  ├→ Sí: COMMENT_TEXT → PANAS_CHOICE
  └→ No: PANAS_CHOICE
    ├→ Sí: PANAS_TEXT → FINISH
    └→ No: FINISH
```

### Detalle por Estado - TALLER

#### **Estado 0: TYPE_CHOICE** (Selección inicial)
- **Descripción:** Elige entre TALLER o SERVICIO
- **Transiciones esperadas:**
  - TALLER → `MACHINE_NAME`
  - SERVICIO → `SERVICE_CLIENT_SEARCH`
- **Botón atrás desde aquí:** N/A (es el inicio)
- **Botones atrás que apuntan aquí:**
  - `MACHINE_NAME` → `back|TYPE_CHOICE` ✅
  - `SERVICE_CLIENT_SEARCH` → `back|TYPE_CHOICE` ✅
- **Código:** Líneas 262-276

#### **Estado 1: MACHINE_NAME** (Selección máquina)
- **Descripción:** Elige nombre de máquina (Shaker, Barredora, etc.)
- **Entrada:** Callback `type_selected()`
- **Salida:** Callback `machine_name_selected()`
- **Botón atrás esperado:** Volver a `TYPE_CHOICE`
- **Botón implementado:** `back|TYPE_CHOICE` ✅
- **Transición siguiente:** `MACHINE_NUM`
- **Código:** Líneas 325-327 (función), línea 1097 (handler atrás)

#### **Estado 2: MACHINE_NUM** (Selección número)
- **Descripción:** Elige número de máquina (1-10)
- **Entrada:** Callback `machine_name_selected()`
- **Salida:** Callback `machine_num_selected()`
- **Botón atrás esperado:** Volver a `MACHINE_NAME`
- **Botón implementado:** `back|MACHINE_NAME` ✅
- **Transición siguiente:** `COMPONENT`
- **Código:** Líneas 329-334 (función), línea 1104 (handler atrás)

#### **Estado 3: COMPONENT** (Selección componente principal)
- **Descripción:** Elige componente (MOTOR, CILINDROS, etc.)
- **Entrada:** Callback `machine_num_selected()`
- **Salida:** Callback `component_selected()`
- **Bifurcación:**
  - Si component tiene subs → `SUBCOMPONENT`
  - Si NO tiene subs → `CHECKLIST` (directo)
- **Botón atrás esperado:** Volver a `MACHINE_NUM`
- **Botón implementado:** `back|MACHINE_NUM` ✅
- **Código:** Líneas 353-377 (función), línea 1111 (handler atrás)

#### **Estado 4: SUBCOMPONENT** (Selección sub-componente)
- **Descripción:** Elige sub-componente (MANGUERAS, BARREDORES, etc.)
- **Entrada:** Callback `component_selected()` (si tiene subs)
- **Salida:** Callback `subcomponent_selected()`
- **Botón atrás esperado:** Volver a `COMPONENT`
- **Botón implementado:** `back|COMPONENT` ✅
- **Transición siguiente:** `CHECKLIST`
- **Código:** Líneas 413-435 (función), línea 1120 (handler atrás)

#### **Estado 5: CHECKLIST** (Multi-select items)
- **Descripción:** Checkbox items de un subcomponente/componente
- **Entrada:** 
  - Callback `subcomponent_selected()` (si hay subs)
  - Callback `component_selected()` (si NO hay subs)
- **Salida:** Callback `toggle_checklist_item()` o botón "Finalizar"
- **Botón atrás esperado:** Volver a `SUBCOMPONENT` o `COMPONENT`
- **Botón implementado:** `back|SUBCOMPONENT` ✅
- **Transición siguiente:** `COMMENT_CHOICE` (al presionar Finalizar)
- **Código:** Líneas 449-467 (función atrás), línea 1135

#### **Estado 6: COMMENT_CHOICE** (¿Comentarios?)
- **Descripción:** Pregunta si desea agregar comentario
- **Entrada:** Callback `toggle_checklist_item()` con "Finalizar"
- **Bifurcación:**
  - Sí → `COMMENT_TEXT`
  - No → `PANAS_CHOICE`
- **Botón atrás esperado:** Volver a `CHECKLIST`
- **Botón implementado:** `back|CHECKLIST` ✅
- **Código:** Líneas 530-537 (función comment_choice), línea 1140

#### **Estado 7: COMMENT_TEXT** (Entrada comentario)
- **Descripción:** Campo de texto libre para comentario
- **Entrada:** Usuario ingresa texto después de "¿Comentarios? Sí"
- **Manejo:** `receive_comment()`
- **Botón atrás:** ⚠️ PROBLEMA - No puede haber botón en MessageHandler
- **Código:** Líneas 540-542 (función receive_comment)

#### **Estado 8: PANAS_CHOICE** (¿PANAS?)
- **Descripción:** Pregunta si desea agregar detalle PANAS
- **Entrada:** 
  - De `COMMENT_TEXT` (si ingresó comentario)
  - De `COMMENT_CHOICE` (si selecciona No)
- **Bifurcación:**
  - Sí → `PANAS_TEXT`
  - No → `FINISH`
- **Botón atrás esperado:** Volver a `COMMENT_CHOICE`
- **Botón implementado:** `back|COMMENT_CHOICE` ✅
- **Código:** Líneas 556-564 (función panas_choice), línea 1144

#### **Estado 9: PANAS_TEXT** (Entrada PANAS)
- **Descripción:** Campo de texto libre para PANAS
- **Entrada:** Usuario ingresa texto
- **Manejo:** `receive_panas_text()`
- **Botón atrás:** ⚠️ PROBLEMA - No puede haber botón en MessageHandler
- **Transición siguiente:** `FINISH`
- **Código:** Líneas 567-573 (función receive_panas_text)

---

## 🛣️ FLUJO SERVICIO - Cliente y Servicios Agrícolas

### Secuencia Esperada (Con Detalles - PODA/Podadora):
```
TYPE_CHOICE 
  ↓ (selecciona SERVICIO)
SERVICE_CLIENT_SEARCH 
  ↓ (ingresa texto)
SERVICE_CLIENT_SELECT 
  ↓ (selecciona cliente)
SERVICE_SERVICE_SELECT 
  ↓ (selecciona PODA/COSECHA/BARRIDO)
SERVICE_SUBSERVICE_SELECT 
  ↓ (selecciona Podadora/Nogales/Barredora)
SERVICE_DETAIL_HILERAS 
  ↓ (selecciona Hileras)
SERVICE_DETAIL_CARAS 
  ↓ (selecciona Caras)
SERVICE_DETAIL_PASADAS 
  ↓ (selecciona Pasadas)
SERVICE_HOROMETRO_INICIO 
  ↓ (ingresa número)
SERVICE_HOROMETRO_TERMINO 
  ↓ (ingresa número)
SERVICE_HECTAREAS 
  ↓ (ingresa número)
COMMENT_CHOICE 
  ├→ Sí: COMMENT_TEXT → PANAS_CHOICE
  └→ No: PANAS_CHOICE
    ├→ Sí: PANAS_TEXT → FINISH
    └→ No: FINISH
```

### Secuencia Esperada (Sin Detalles - COSECHA/BARRIDO):
```
... (igual hasta SERVICE_SUBSERVICE_SELECT)
SERVICE_SUBSERVICE_SELECT (selecciona sin detalles)
  ↓ SALTA directamente a:
SERVICE_HOROMETRO_INICIO
  ↓ (el resto igual)
```

### Detalle por Estado - SERVICIO

#### **Estado 10: SERVICE_CLIENT_SEARCH** (Búsqueda cliente)
- **Descripción:** Campo de texto para buscar cliente por nombre
- **Entrada:** Usuario escribe parte del nombre
- **Manejo:** `service_client_search()`
- **Salida:** Si hay coincidencias → `SERVICE_CLIENT_SELECT`
- **Botón atrás esperado:** Volver a `TYPE_CHOICE`
- **Botón implementado:** `back|TYPE_CHOICE` ✅
- **Problema:** ⚠️ MessageHandler no procesa callbacks de atrás
- **Código:** Líneas 576-595, línea 1076

#### **Estado 11: SERVICE_CLIENT_SELECT** (Selección cliente)
- **Descripción:** Lista paginada de clientes que coinciden
- **Entrada:** Callback `service_client_search()` con resultados
- **Salida:** Callback `service_client_selected()` o navegación de páginas
- **Paginación:** 5 clientes por página con numeración correlativa
- **Botón atrás esperado:** Volver a `SERVICE_CLIENT_SEARCH`
- **Botón implementado:** `back|SERVICE_CLIENT_SEARCH` ✅
- **Transición siguiente:** `SERVICE_SERVICE_SELECT`
- **Código:** Líneas 597-649, línea 1080

#### **Estado 12: SERVICE_SERVICE_SELECT** (Selección servicio principal)
- **Descripción:** Elige entre PODA, COSECHA, BARRIDO DE HOJAS
- **Entrada:** Callback `service_client_selected()`
- **Salida:** Callback `service_service_selected()`
- **Bifurcación:**
  - Si tiene servicios secundarios → `SERVICE_SUBSERVICE_SELECT`
  - Si NO tiene subs → `COMMENT_CHOICE` (no hay detalles)
- **Botón atrás esperado:** Volver a `SERVICE_CLIENT_SELECT`
- **Botón implementado:** `back|SERVICE_CLIENT_SELECT` ✅
- **Código:** Líneas 651-674, línea 1084

#### **Estado 13: SERVICE_SUBSERVICE_SELECT** (Selección subservicio)
- **Descripción:** Elige Podadora específica/Cultivo/Barredora
- **Entrada:** Callback `service_service_selected()`
- **Salida:** Callback `service_subservice_selected()`
- **Bifurcación:**
  - Si tiene detalles (aplicables) → `SERVICE_DETAIL_HILERAS`
  - Si NO tiene detalles → `SERVICE_HOROMETRO_INICIO`
- **Botón atrás esperado:** Volver a `SERVICE_SERVICE_SELECT`
- **Botón implementado:** `back|SERVICE_SERVICE_SELECT` ✅ (FUE CORREGIDO)
- **Código:** Líneas 676-706, línea 1104

#### **Estado 14: SERVICE_DETAIL_HILERAS** (Selección Hileras)
- **Descripción:** Elige patrón de Hileras (cada 1, 2, 3 o 4)
- **Entrada:** Callback `service_subservice_selected()` con detalles
- **Salida:** Callback `detail_hileras_selected()`
- **Botón atrás esperado:** Volver a `SERVICE_SUBSERVICE_SELECT`
- **Botón implementado:** `back|SERVICE_SUBSERVICE_SELECT` ✅ (CORREGIDO de back|SERVICE_DETAIL_HILERAS)
- **Transición siguiente:** `SERVICE_DETAIL_CARAS`
- **Código:** Líneas 708-720, línea 725

#### **Estado 15: SERVICE_DETAIL_CARAS** (Selección Caras)
- **Descripción:** Elige tipo de poda (1 cara, 3 caras, topping)
- **Entrada:** Callback `detail_hileras_selected()`
- **Salida:** Callback `detail_caras_selected()`
- **Botón atrás esperado:** Volver a `SERVICE_DETAIL_HILERAS`
- **Botón implementado:** `back|SERVICE_DETAIL_HILERAS` ✅ (CORREGIDO de back|SERVICE_DETAIL_CARAS)
- **Transición siguiente:** `SERVICE_DETAIL_PASADAS`
- **Código:** Líneas 722-734, línea 756

#### **Estado 16: SERVICE_DETAIL_PASADAS** (Selección Pasadas)
- **Descripción:** Elige número de pasadas (1 o 2)
- **Entrada:** Callback `detail_caras_selected()`
- **Salida:** Callback `detail_pasadas_selected()`
- **Botón atrás esperado:** Volver a `SERVICE_DETAIL_CARAS`
- **Botón implementado:** `back|SERVICE_DETAIL_CARAS` ✅ (CORREGIDO de back|SERVICE_DETAIL_PASADAS)
- **Transición siguiente:** `SERVICE_HOROMETRO_INICIO`
- **Código:** Líneas 736-752, línea 789

#### **Estado 17: SERVICE_HOROMETRO_INICIO** (Horómetro inicio)
- **Descripción:** Ingresa número de horómetro al inicio
- **Entrada:** Callback `detail_pasadas_selected()` O `service_subservice_selected()` (sin detalles)
- **Manejo:** `receive_horometro_inicio()`
- **Botón atrás esperado:** Depende si vino de detalles
  - Si de detalles: volver a `SERVICE_DETAIL_PASADAS`
  - Si no detalles: volver a `SERVICE_SUBSERVICE_SELECT`
- **Botón implementado:** `back|SERVICE_HOROMETRO_INICIO` ⚠️ PROBLEMA
- **Transición siguiente:** `SERVICE_HOROMETRO_TERMINO`
- **Código:** Líneas 1177-1183, línea 1150

**⚠️ PROBLEMA CRÍTICO EN ESTADO 17:**
El `back_button_handler` en línea 1150-1166 intenta detectar si vino de detalles o no mediante:
```python
elif target_state == "SERVICE_HOROMETRO_INICIO":
    # Checa si tiene detalles
    subservice_id = context.user_data['workflow'].get('subservice', '')
    applicable_details = [d for d in DETALLES_SERVICIOS.values() if subservice_id in d.get('aplica_a', [])]
    
    if applicable_details:
        # Vuelve a SERVICE_DETAIL_PASADAS
    else:
        # Vuelve a SERVICE_SUBSERVICE_SELECT
```

**Pero:** El botón atrás en el `receive_horometro_inicio()` es un MessageHandler, que **NO PUEDE PROCESAR CALLBACKS**. Debería ser un campo de texto con botón previo, no un botón inline.

#### **Estado 18: SERVICE_HOROMETRO_TERMINO** (Horómetro término)
- **Descripción:** Ingresa número de horómetro al final
- **Manejo:** `receive_horometro_termino()`
- **Botón atrás esperado:** Volver a `SERVICE_HOROMETRO_INICIO`
- **Botón implementado:** `back|SERVICE_HOROMETRO_TERMINO` ⚠️ PROBLEMA (MessageHandler)
- **Transición siguiente:** `SERVICE_HECTAREAS`
- **Código:** Líneas 1185-1191

#### **Estado 19: SERVICE_HECTAREAS** (Hectáreas)
- **Descripción:** Ingresa cantidad de hectáreas
- **Manejo:** `receive_hectareas()`
- **Botón atrás esperado:** Volver a `SERVICE_HOROMETRO_TERMINO`
- **Botón implementado:** `back|SERVICE_HECTAREAS` ⚠️ PROBLEMA (MessageHandler)
- **Transición siguiente:** `COMMENT_CHOICE`
- **Código:** Líneas 1193-1200

---

## ❌ PROBLEMAS IDENTIFICADOS

### **CATEGORÍA 1: Detail States Loops** (SOLUCIONADO ✅)

| Problema | Línea | Antes | Ahora | Estado |
|----------|-------|-------|-------|--------|
| Hileras vuelve a sí mismo | 725 | `back\|SERVICE_DETAIL_HILERAS` | `back\|SERVICE_SUBSERVICE_SELECT` | ✅ FIJO |
| Caras vuelve a sí mismo | 756 | `back\|SERVICE_DETAIL_CARAS` | `back\|SERVICE_DETAIL_HILERAS` | ✅ FIJO |
| Pasadas vuelve a sí mismo | 789 | `back\|SERVICE_DETAIL_PASADAS` | `back\|SERVICE_DETAIL_CARAS` | ✅ FIJO |

### **CATEGORÍA 2: Text Field Back Buttons** (⚠️ ARQUITECTURA)

Los campos de texto libre (`SERVICE_HOROMETRO_INICIO`, `SERVICE_HOROMETRO_TERMINO`, `SERVICE_HECTAREAS`, `COMMENT_TEXT`, `PANAS_TEXT`) usan:
```python
MessageHandler(filters.TEXT & ~filters.COMMAND, receive_horometro_inicio)
```

Esto acepta **texto**, no **callbacks**. El botón atrás mostrado es decorativo pero NO funciona.

**Líneas problemáticas:**
- 1179: `receive_horometro_inicio()` - MessageHandler
- 1187: `receive_horometro_termino()` - MessageHandler  
- 1195: `receive_hectareas()` - MessageHandler
- 540: `receive_comment()` - MessageHandler
- 567: `receive_panas_text()` - MessageHandler

**Soluciones posibles:**
1. ❌ Cambiar a CallbackQueryHandler - No, necesita entrada de texto
2. ✅ Botón separado ANTES del campo (requiere interfaz diferente)
3. ✅ Permitir "atrás" como entrada de texto (ejemplo: usuario escribe "back")
4. ✅ Eliminar botones atrás en campos de texto (dejar solo en selecciones)

### **CATEGORÍA 3: SERVICE_HOROMETRO_INICIO Navigation Complexity**

**Línea 1150-1166:** El handler intenta ser inteligente:
- Si vino de detalles (tiene aplicables) → vuelve a PASADAS
- Si vino sin detalles → vuelve a SUBSERVICE_SELECT

**Pero:** El botón atrás en `receive_horometro_inicio()` (línea 1179) es MessageHandler, así que esta lógica nunca se ejecuta.

---

## 📊 Tabla Maestra de Navegación

| Estado | Entra desde | Sale hacia | Back esperado | Back implementado | ✅ Status |
|--------|------------|----------|--------------|------------------|-----------|
| TYPE_CHOICE | /start | MACHINE_NAME o SERVICE_CLIENT_SEARCH | - | - | ✅ |
| MACHINE_NAME | type_selected() | MACHINE_NUM | TYPE_CHOICE | TYPE_CHOICE | ✅ |
| MACHINE_NUM | machine_name_selected() | COMPONENT | MACHINE_NAME | MACHINE_NAME | ✅ |
| COMPONENT | machine_num_selected() | SUBCOMPONENT o CHECKLIST | MACHINE_NUM | MACHINE_NUM | ✅ |
| SUBCOMPONENT | component_selected() | CHECKLIST | COMPONENT | COMPONENT | ✅ |
| CHECKLIST | subcomponent_selected() o component_selected() | COMMENT_CHOICE | SUBCOMPONENT o COMPONENT | SUBCOMPONENT | ⚠️ FALTA LOGIC |
| COMMENT_CHOICE | toggle_checklist_item() | COMMENT_TEXT o PANAS_CHOICE | CHECKLIST | CHECKLIST | ✅ |
| COMMENT_TEXT | receive_comment() o comment_choice() | PANAS_CHOICE | COMMENT_CHOICE | ❌ (MessageHandler) | ❌ |
| PANAS_CHOICE | ask_panas() | PANAS_TEXT o FINISH | COMMENT_CHOICE | COMMENT_CHOICE | ✅ |
| PANAS_TEXT | panas_choice() | FINISH | PANAS_CHOICE | ❌ (MessageHandler) | ❌ |
| SERVICE_CLIENT_SEARCH | type_selected() | SERVICE_CLIENT_SELECT | TYPE_CHOICE | TYPE_CHOICE | ✅ |
| SERVICE_CLIENT_SELECT | service_client_search() | SERVICE_SERVICE_SELECT | SERVICE_CLIENT_SEARCH | SERVICE_CLIENT_SEARCH | ✅ |
| SERVICE_SERVICE_SELECT | service_client_selected() | SERVICE_SUBSERVICE_SELECT o COMMENT_CHOICE | SERVICE_CLIENT_SELECT | SERVICE_CLIENT_SELECT | ✅ |
| SERVICE_SUBSERVICE_SELECT | service_service_selected() | SERVICE_DETAIL_HILERAS o SERVICE_HOROMETRO_INICIO | SERVICE_SERVICE_SELECT | SERVICE_SERVICE_SELECT | ✅ (FIJO) |
| SERVICE_DETAIL_HILERAS | service_subservice_selected() | SERVICE_DETAIL_CARAS | SERVICE_SUBSERVICE_SELECT | SERVICE_SUBSERVICE_SELECT | ✅ (FIJO) |
| SERVICE_DETAIL_CARAS | detail_hileras_selected() | SERVICE_DETAIL_PASADAS | SERVICE_DETAIL_HILERAS | SERVICE_DETAIL_HILERAS | ✅ (FIJO) |
| SERVICE_DETAIL_PASADAS | detail_caras_selected() | SERVICE_HOROMETRO_INICIO | SERVICE_DETAIL_CARAS | SERVICE_DETAIL_CARAS | ✅ (FIJO) |
| SERVICE_HOROMETRO_INICIO | detail_pasadas_selected() o service_subservice_selected() | SERVICE_HOROMETRO_TERMINO | PASADAS o SUBSERVICE | ❌ (MessageHandler) | ❌ |
| SERVICE_HOROMETRO_TERMINO | receive_horometro_inicio() | SERVICE_HECTAREAS | SERVICE_HOROMETRO_INICIO | ❌ (MessageHandler) | ❌ |
| SERVICE_HECTAREAS | receive_horometro_termino() | COMMENT_CHOICE | SERVICE_HOROMETRO_TERMINO | ❌ (MessageHandler) | ❌ |

---

## 🔧 CHECKLIST DE CORRECCIONES

### ✅ Completadas:
- [x] Fijar SERVICE_DETAIL_HILERAS back button (línea 725)
- [x] Fijar SERVICE_DETAIL_CARAS back button (línea 756)
- [x] Fijar SERVICE_DETAIL_PASADAS back button (línea 789)
- [x] Fijar SERVICE_SUBSERVICE_SELECT back button (línea 1104)

### ⚠️ En Progreso:
- [ ] Decidir arquitectura para campos de texto con navegación atrás
- [ ] Revisar CHECKLIST back button (a SUBCOMPONENT o COMPONENT)

### ❌ Sin Resolver:
- [ ] SERVICE_HOROMETRO_INICIO no puede tener back button (MessageHandler)
- [ ] SERVICE_HOROMETRO_TERMINO no puede tener back button (MessageHandler)
- [ ] SERVICE_HECTAREAS no puede tener back button (MessageHandler)
- [ ] COMMENT_TEXT no puede tener back button (MessageHandler)
- [ ] PANAS_TEXT no puede tener back button (MessageHandler)

---

## 💡 Recomendaciones

### Opción A: Elegancia de UX
Los campos de texto son **puntos terminales** sin navegación atrás. Una vez que ingresas un valor, avanzas. Los usuarios pueden /start para reiniciar.

**Ventaja:** Simple, consistente  
**Desventaja:** Menos flexible

### Opción B: Full Navigation
Cambiar arquitectura:
1. Antes del campo de texto, mostrar botón "Cancelar/Atrás"
2. Si presiona, vuelve al paso anterior
3. Si ingresa texto, avanza normalmente

**Ventaja:** Total control  
**Desventaja:** Requiere refactorizar handlers

### Opción C: Híbrida (RECOMENDADA)
- Campos de texto DESPUÉS de selecciones complejas NO tienen back
- Campos iniciales (búsqueda cliente) SÍ tienen back
- Usar /start en cualquier momento para reiniciar

---

## 🧪 Plan de Pruebas Sistemáticas

### Flujo TALLER Completo:
```
/start → TALLER → Shaker → 1 → MOTOR → (no subs) → CHECKLIST
→ Finalizar → Sí comentarios → "Mi comentario" 
→ Sí PANAS → "Ánimo positivo" → ✅ FINISH
```

**Con navegación atrás en cada paso.**

### Flujo SERVICIO con Detalles (PODA/Podadora):
```
/start → SERVICIO → "AGRICOLA" (busca cliente) → Selecciona
→ PODA → Podadora 1 → Cada 1 Hilera → Poda 1 Cara → 1 Pasada
→ 8500 (horómetro inicio) → 8600 (término) → 5 (hectáreas)
→ Sí comentarios → "Listo" → No PANAS → ✅ FINISH
```

### Flujo SERVICIO sin Detalles (COSECHA/NOGALES):
```
/start → SERVICIO → "AGRICOLA" → COSECHA → NOGALES
→ 3000 → 3100 → 2 → No → No → ✅ FINISH
```

---

## 📝 Notas Técnicas

- **Token de atrás:** `back|{TARGET_STATE}` - `target_state` es WHERE to go
- **Not FROM where we are** - Es el destino, no el origen
- **MessageHandler vs CallbackQueryHandler:** 
  - MessageHandler = recibe texto
  - CallbackQueryHandler = recibe callback_data de botones
  - No se pueden mezclar en el mismo handler
- **ConversationHandler:** Maneja los 20 estados como máquina de estados
- **Context.user_data:** Persiste datos entre estados (workflow dict)

