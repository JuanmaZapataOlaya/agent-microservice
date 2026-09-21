# Base de Conocimiento: Plataforma de Gestión y Reencuentro de Mascotas

## 1. Visión General del Sistema
La plataforma está diseñada para facilitar la localización, reporte y reencuentro seguro de mascotas perdidas o encontradas. Incorpora búsquedas avanzadas (semánticas y geoespaciales), un sistema de verificación basado en Agentes de Inteligencia Artificial para la validación de evidencia fotográfica, un flujo de notificaciones/contacto entre usuarios y un historial público/privado de casos resueltos como medida de seguridad y registro histórico.

---

## 2. Gestión de Reportes y Publicaciones (Posts)

### 2.1 Crear un Reporte de Mascota
Cualquier usuario registrado puede crear un reporte/publicación en la plataforma cuando pierde o encuentra un animal.

*   **Tipos de Reporte:**
    *   *Mascota Perdida:* Registrado por el dueño o tutor en búsqueda de su mascota.
    *   *Mascota Encontrada:* Registrado por un ciudadano que halló un animal en la calle o lo tiene en resguardo temporal.
*   **Campos del Reporte:**
    *   **Especie:** (Obligatorio) Perro, gato, ave, etc.
    *   **Raza:** (Obligatorio/Aproximado) Especificar raza o "Mestizo/Sin raza definida".
    *   **Nombre:** (Opcional) Aplica principalmente si el reporte es de una mascota perdida o si la mascota encontrada responde a una placa.
    *   **Ubicación/Lugar de hallazgo o pérdida:** (Obligatorio) Dirección, punto de referencia o coordenadas.
    *   **Descripción / Características:** Detalles físicos (color, manchas, cicatrices, collar) y de comportamiento.
    *   **Fotografías del reporte:** Imágenes de referencia inicial de la mascota.

### 2.2 Edición de Perfil de Usuario
*   Los usuarios pueden personalizar y actualizar sus datos de perfil (nombre, teléfono, método de contacto preferido).
*   Esta información se compartirá **únicamente** con otro usuario cuando exista una interacción legítima sobre un reporte (por ejemplo, al responder a una solicitud de reclamo o contacto previa verificación).

---

## 3. Búsqueda y Filtros de Mascotas

Para optimizar el hallazgo de animales, el sistema cuenta con capacidades de búsqueda híbrida y espacial:

*   **Búsqueda por Distancia / Geolocalización:** Filtra publicaciones según el radio kilométrico respecto a la ubicación del usuario o un punto especificado en el mapa.
*   **Búsqueda Híbrida (Semántica y Textual):**
    *   *Búsqueda Textual:* Coincidencia de palabras clave exactas (ej. "Husky siberiano ojos azules").
    *   *Búsqueda Semántica (IA):* Entiende el contexto del texto de búsqueda aunque no coincida exactamente con las palabras del reporte (ej. si el usuario busca "perro pequeño blanco orejas caídas", encontrará reportes afines mediante embeddings vectoriales).
*   **Filtros Combinados:** Permite cruzar estado (perdido/encontrado), distancia, especie y atributos físicos simultáneamente.

---

## 4. Flujo de Contacto y Verificación de Identidad mediante Evidencia

Para evitar fraudes, robos o entregas erróneas a personas con intenciones maliciosas, la interacción con un reporte sigue un riguroso proceso de validación.

### 4.1 Proceso de Contacto e Interacción
1.  Un usuario explora las publicaciones y reconoce a su mascota o cree tener información del dueño.
2.  Al hacer clic en **"Contactar"** o **"Reclamar Mascota"**, el sistema le exigirá subir evidencia previa a la apertura del chat o envío de datos.

### 4.2 Requisito de Evidencia (Imágenes)
*   **Cantidad requerida:** Exactamente dos (2) imágenes.
*   **Formatos permitidos:** PNG, JPG, JPEG y formatos nativos de cámara (RAW / HEIC).
*   **Propósito:** Demostrar que quien intenta contactar es el verdadero dueño o tiene pruebas reales de la pertenencia/hallazgo (ej. fotos antiguas con la mascota, fotos del animal en casa, marcas distintivas específicas).

### 4.3 Agente de Verificación de Credibilidad de Imágenes (IA)
Antes de entregar la notificación al creador del reporte, las dos imágenes adjuntas son analizadas por un **Agente de IA especializado en Análisis Forense de Imágenes**:

*   **Funciones del Agente de IA:**
    *   **Detección de Generación por IA:** Analiza si las fotos fueron creadas o alteradas mediante inteligencia artificial generativa.
    *   **Verificación de Origen Web:** Revisa si las imágenes son capturas o descargas tomadas de motores de búsqueda públicos (Google Images, bancos de fotos, redes sociales).
    *   **Análisis de Naturalidad y Metadatos:** Evalúa si la estructura de iluminación, ruido de cámara y metadatos sugieren una fotografía natural tomadas por un dispositivo físico.
*   **Generación de Indicaciones y Consejos (Alertas):**
    *   El agente **NO bloquea automáticamente** de forma tajante (a menos que sea flagrante), sino que adjunta una **evaluación y recomendaciones** en la notificación enviada al destinatario.
    *   *Ejemplo de Alerta:* ⚠️ "Atención: La imagen 1 muestra un 92% de probabilidad de haber sido generada por IA o descargada de internet. Proceda con precaución y solicite más pruebas antes de acordar un encuentro."
    *   *Ejemplo de Confirmación:* ✅ "Las imágenes parecen ser fotografías naturales sin rastros de edición digital o coincidencias públicas en la red."

### 4.4 Notificación y Establecimiento de Contacto
*   El usuario que creó el reporte recibe una **notificación en su cuenta** informando que alguien ha solicitado contacto.
*   La notificación incluye la información de perfil permitida del interesado, las 2 imágenes de evidencia y el informe/consejo del Agente de IA.
*   A partir de este punto, si el dueño del reporte considera válida la información, se habilitan los canales directos de comunicación.

---

## 5. Historial de Mascotas Resueltas y Seguridad de Mitigación

Una vez finalizado el proceso de reencuentro o devolución, el reporte cambia su estado a **"Resuelto"**.

*   **Registro del Historial:** La plataforma conserva un historial público/privado de las mascotas que completaron exitosamente la restitución entre ambas partes.
*   **Función del Historial:**
    *   *Memoria y Recordatorio:* Funciona como un registro feliz y comprobable del reencuentro de la mascota.
    *   *Mecanismo de Mitigación y Seguridad:* En casos donde haya habido sospechas de robo, disputa de propiedad o apropiación indebida previa, este historial sirve como trazabilidad auditable de quién devolvió a la mascota, a quién se le entregó, con qué fotos de evidencia se validó el proceso y en qué fecha.
    *   *Reputación de Usuario:* Permite verificar la actividad histórica positiva dentro de la comunidad.

---

## 6. Preguntas Frecuentes (FAQ) para el Agente RAG

**P: ¿Es obligatorio ingresar el nombre de la mascota al crear un reporte?**  
R: No, el campo "Nombre" es opcional, ya que en los casos de mascotas encontradas generalmente se desconoce cómo se llama el animal.

**P: ¿Qué formatos de imagen se aceptan al momento de solicitar contacto con un dueño?**  
R: Se aceptan formatos PNG, JPG, JPEG y formatos crudos directos de cámara (como HEIC o RAW).

**P: ¿Por qué la aplicación me pide dos fotos para contactar al dueño de un reporte?**  
R: Se solicitan dos imágenes como evidencia para demostrar la autenticidad del reclamo. Estas imágenes son evaluadas por un Agente de IA para verificar que no sean falsas, generadas por computadora o sacadas de internet.

**P: ¿Qué ocurre si el Agente de IA detecta que una foto enviada es falsa o sacada de internet?**  
R: El sistema notificará al receptor del reporte incluyendo una alerta o consejo donde le advertirá sobre la falta de credibilidad de la imagen, sugiriendo que tome precauciones antes de entregar la mascota.

**P: ¿Cómo funciona la búsqueda para encontrar a mi mascota?**  
R: Puedes usar filtros por rango de distancia geográfica, o realizar búsquedas híbridas que combinan coincidencias exactas de texto con búsqueda semántica basada en el significado de la descripción de la mascota.

**P: ¿Qué es el Historial de Mascotas y para qué sirve?**  
R: Es un registro de las mascotas cuyo reporte ya fue resuelto. Sirve como recuerdo del reencuentro y como una medida de seguridad y trazabilidad que mitiga problemas de robos o falsos reclamos al dejar constancia del proceso de intercambio.