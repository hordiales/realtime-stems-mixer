# SuperCollider Eurovision Stem Mixer - Guía Completa

Este sistema implementa la misma funcionalidad del `realtime_stem_mixer.py` pero envía mensajes OSC a SuperCollider para la reproducción de audio en tiempo real, eliminando problemas de PyAudio y proporcionando audio profesional.

## 🎛️ Arquitectura del Sistema

```
Python Mixer (Control) ←→ OSC Messages ←→ SuperCollider (Audio)
     ↓                                           ↓
- Gestión de stems                         - Reproducción de audio
- Control BPM/Key                          - Procesamiento DSP  
- Interface CLI/OSC                        - Mezcla profesional
- Crossfading                              - Salida de audio
```

## 📂 Archivos del Sistema

### Componentes Principales
- **`supercollider_stem_mixer.py`** - Mixer principal con control OSC
- **`supercollider_audio_server.scd`** - Servidor de audio SuperCollider
- **`test_supercollider_mixer.py`** - Suite de pruebas
- **`mixer_config.json`** - Configuración del sistema

## 🚀 Instalación y Configuración

### Requisitos
1. **SuperCollider** instalado y funcionando
2. **Python** con dependencias:
   ```bash
   pip install python-osc numpy soundfile librosa
   ```

### Configuración Actual (mixer_config.json)
```json
{
  "audio": {
    "sample_rate": 48000,        // Coincide con SuperCollider
    "chunk_size": 512,           // Buffer optimizado
    "enable_pitch_shifting": false,
    "enable_time_stretching": false,
    "soft_limiting": true,
    "master_volume": 0.8
  }
}
```

## 🎵 Uso del Sistema

### Paso 1: Iniciar SuperCollider
```supercollider
// En SuperCollider, ejecutar:
"supercollider_audio_server.scd".loadRelative;
```

### Paso 2: Iniciar el Mixer Python
```bash
python supercollider_stem_mixer.py
```

### Paso 3: Controles Disponibles

#### Comandos CLI (en el mixer Python):
```bash
# Control de BPM y key
bpm 140           # Cambiar BPM instantáneamente
key Am            # Cambiar tonalidad

# Control de decks
a 0               # Cargar canción 0 en deck A
b 3               # Cargar canción 3 en deck B

# Stems individuales  
a.bass 2          # Cargar bass de canción 2 en deck A
b.drums 5         # Cargar drums de canción 5 en deck B

# Crossfader
cross 0.5         # Mezcla 50/50 entre decks
cross 0           # Solo deck A
cross 1           # Solo deck B

# Volúmenes de stems
bass 0.9          # Volume de bass
drums 0.7         # Volume de drums
vocals 0.8        # Volume de vocals
piano 0.6         # Volume de piano
other 0.5         # Volume de otros instrumentos

# Utilidades
random            # Mezcla aleatoria
status            # Mostrar estado actual
songs             # Listar canciones disponibles
quit              # Salir
```

#### Mensajes OSC (para control externo):
```bash
# Enviar a localhost:5005
/bpm 160                    # Cambio de BPM
/crossfade 0.3             # Crossfader a 30%
/deck/a/load 2             # Cargar canción 2 en deck A
/stem/vocals 0.5           # Volume de vocals a 50%
/random                    # Mezcla aleatoria
/status                    # Solicitar estado
```

## 📡 Protocolo OSC Entre Python y SuperCollider

### De Python → SuperCollider (puerto 57120):
```
/load_buffer [bufferID] [filePath] [stemName]
/play_stem [bufferID] [rate] [volume] [loop] [startPos]  
/stop_stem [bufferID]
/stem_volume [bufferID] [volume]
/crossfade_levels [deckALevel] [deckBLevel]
/set_key [key]
/mixer_init [sampleRate] [numSongs]
/mixer_cleanup
/test_tone [frequency] [duration]
/get_status
```

### De Control Externo → Python (puerto 5005):
```
/bpm [value]
/crossfade [position]
/deck/a/load [songID]
/deck/b/load [songID]
/stem/bass [volume]
/stem/drums [volume]
/stem/vocals [volume]
/stem/piano [volume]
/stem/other [volume]
/random
/status
```

## 🎛️ Características Principales

### Control en Tiempo Real
- **BPM instantáneo**: Cambios de 60-200 BPM sin cortes
- **Crossfading profesional**: Mezcla suave entre decks A y B
- **Stems individuales**: Control independiente de cada instrumento
- **Sincronización**: Todos los stems mantienen sincronía musical

### Audio Profesional (SuperCollider)
- **Sample rate**: 48kHz (configurable en ambos sistemas)
- **Latencia baja**: ~10ms con buffer de 512 samples
- **Soft limiting**: Previene distorsión automáticamente
- **DSP avanzado**: Procesamiento de audio de calidad profesional

### Sin Problemas de PyAudio
- **Salida estable**: SuperCollider maneja toda la salida de audio
- **Sin glitches**: Eliminados los errores de buffer mismatch
- **Multiplataforma**: Funciona en Mac, Linux, Windows
- **Escalable**: Soporta procesamiento de audio complejo

## 🧪 Pruebas del Sistema

### Ejecutar Suite de Pruebas
```bash
python test_supercollider_mixer.py
```

### Pruebas Incluidas
1. **Conexión OSC**: Verifica comunicación con SuperCollider
2. **Inicialización**: Prueba carga de configuración y canciones
3. **Simulación de Stems**: Simula carga y reproducción

### Resolución de Problemas

#### SuperCollider no responde:
```supercollider
// Verificar que SuperCollider esté ejecutando el servidor
s.boot;
// Ejecutar el archivo de servidor
"supercollider_audio_server.scd".loadRelative;
```

#### No se encuentran canciones:
```bash
# Verificar estructura de archivos stems
ls stems/
# Debería mostrar archivos como: 01-01_bass.wav, 01-01_drums.wav, etc.
```

#### Errores de configuración:
```bash
# Mostrar configuración actual
python config_loader.py show

# Crear configuración por defecto
python config_loader.py create
```

## ⚡ Mejoras vs Sistema Original

### Ventajas del Sistema SuperCollider:
1. **Sin PyAudio**: Eliminados todos los problemas de audio streaming
2. **Calidad profesional**: DSP de SuperCollider vs procesamiento Python
3. **Latencia consistente**: Audio thread dedicado en SuperCollider
4. **Escalabilidad**: Fácil agregar efectos y procesamiento avanzado
5. **Estabilidad**: Separación de control (Python) y audio (SuperCollider)

### Manteniendo Funcionalidad Original:
- ✅ Control BPM en tiempo real
- ✅ Crossfading entre decks
- ✅ Stems individuales
- ✅ Interface CLI y OSC
- ✅ Configuración flexible
- ✅ Mezcla aleatoria

## 🎵 Workflow Típico

1. **Preparación**:
   ```bash
   # Iniciar SuperCollider con servidor de audio
   # En SuperCollider: Run supercollider_audio_server.scd
   ```

2. **Iniciar Mixer**:
   ```bash
   python supercollider_stem_mixer.py
   ```

3. **Sesión de DJ**:
   ```bash
   # Cargar canciones
   a 0              # Eurovision song 0 → Deck A
   b 5              # Eurovision song 5 → Deck B
   
   # Ajustar BPM
   bpm 140          # Set tempo
   
   # Mezclar
   cross 0          # Solo A
   cross 0.5        # 50/50 mix
   cross 1          # Solo B
   
   # Controlar stems individuales
   bass 0.2         # Bajar bass
   vocals 1.0       # Subir vocals
   
   # Crear variaciones
   a.drums 3        # Drums de canción 3 → Deck A
   b.bass 7         # Bass de canción 7 → Deck B
   ```

4. **Control Externo (opcional)**:
   ```python
   # Desde otro script Python
   from pythonosc import udp_client
   client = udp_client.SimpleUDPClient("localhost", 5005)
   client.send_message("/bpm", [160])
   client.send_message("/crossfade", [0.7])
   ```

Este sistema proporciona toda la funcionalidad del mixer original pero con audio profesional y sin los problemas técnicos de PyAudio, siendo ideal para performances en vivo y producción musical.