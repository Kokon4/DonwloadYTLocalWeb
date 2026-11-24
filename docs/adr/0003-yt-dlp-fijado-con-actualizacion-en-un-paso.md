# yt-dlp fijado, con un comando para actualizarlo

Todas las dependencias (imagen base, librerías Python, frontend) se fijan a versiones exactas para que la app sea reproducible en cualquier PC. yt-dlp también se fija, pero es una excepción consciente: YouTube cambia a menudo y una versión fija acaba dejando de funcionar. Por eso el repo documenta un único comando que actualiza yt-dlp a la última versión y reconstruye la imagen. Se prefirió esto a actualizar automáticamente en cada arranque porque así siempre se sabe qué versión está en uso y se puede volver atrás si una versión nueva falla.

## Excepción: ffmpeg

ffmpeg se instala desde los paquetes de Debian de la imagen base, sin versión exacta. Fijarla (`ffmpeg=7:7.1.5-…`) haría que la imagen dejara de construirse en cuanto Debian publique un parche de seguridad, porque retira las versiones antiguas de sus repositorios. La versión ya queda acotada por la imagen base fijada (Debian trixie), que solo recibe correcciones, no cambios de versión mayor. _(Decidido en el #10.)_
