# yt-dlp fijado, con un comando para actualizarlo

Todas las dependencias (imagen base, librerías Python, frontend) se fijan a versiones exactas para que la app sea reproducible en cualquier PC. yt-dlp también se fija, pero es una excepción consciente: YouTube cambia a menudo y una versión fija acaba dejando de funcionar. Por eso el repo documenta un único comando que actualiza yt-dlp a la última versión y reconstruye la imagen. Se prefirió esto a actualizar automáticamente en cada arranque porque así siempre se sabe qué versión está en uso y se puede volver atrás si una versión nueva falla.
