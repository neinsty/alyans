# Мануал: проигрывание rosbag Unitree Go2 в Docker-контейнере

Контейнер позволяет проигрывать записанные данные с робота Unitree Go2 (облако лидара, одометрия, IMU, TF) в визуализаторе RViz2, а также разрабатывать на их основе решения навигации и локализации (Python/C++). Работает на Windows 10/11, робот и камеры для работы **не нужны**.

---

## 1. Что понадобится

- Windows 10 Pro/Enterprise/Education или Windows 11 (64-bit)
- 8+ ГБ оперативной памяти
- Свободное место на диске: размер багов + ~1,5× запас
- Интернет (только при установке и первой сборке)

## 2. Установка зависимостей

### 2.1. Платформа виртуализации WSL2

1. Открой **PowerShell от имени администратора** (Пуск → набери `powershell` → правой кнопкой → «Запуск от имени администратора»)
2. Выполни по очереди:
   ```powershell
   Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
   Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
   ```
3. **Перезагрузи компьютер**
4. После перезагрузки открой обычный PowerShell и выполни:
   ```powershell
   wsl --install
   ```
5. Если предложит перезагрузку — перезагрузись ещё раз

### 2.2. Docker Desktop

1. В PowerShell выполни:
   ```powershell
   winget install -e --id Docker.DockerDesktop
   ```
   (либо скачай установщик с https://www.docker.com/products/docker-desktop/)
2. Запусти **Docker Desktop** (Пуск → Docker Desktop)
3. Дождись зелёного статуса **Engine running** в левом нижнем углу окна (первый запуск занимает пару минут)
4. Окно можно свернуть — Docker продолжит работать в трее

### 2.3. X-сервер VcXsrv (для окна RViz)

1. Скачай и установи: https://sourceforge.net/projects/vcxsrv/
2. Запусти **XLaunch**:
   - Multiple windows → **Next**
   - Display number: `0` → **Next**
   - Start no client → **Next**
   - ☑ поставь галочку **Disable access control** → **Next**
   - **Finish**
3. В трее (рядом с часами) появится иконка **X** — она должна быть запущена всегда, пока работает RViz
4. При первом запуске Windows может спросить про брандмауэр — разреши VcXsrv (частные и публичные сети)

> Важно: галочка «Disable access control» обязательна. Без неё контейнер не сможет открыть окно RViz.

## 3. Подготовка проекта

1. Распакуй архив со стендом в любую папку, например `C:\hakaton\mgts`. Структура:
   ```
   mgts/
   ├── Dockerfile
   ├── docker-compose.yml
   ├── play_viz.sh
   ├── go2.rviz
   └── ros2_ws/            <-- сюда кладёшь папки с багами
   ```
2. Скопируй папку с багом (полученную командой `ros2 bag record`) в `ros2_ws`.

   ⚠️ **Особенность путей:** папка бага обычно вложена дважды. Проверь структуру — в самой глубокой папке должны лежать `metadata.yaml` и файлы `*.mcap`:
   ```
   ros2_ws/
   └── bag_for_mapping/
       └── bag_for_mapping/     <-- metadata.yaml и *.mcap здесь
   ```

> Если папка проекта лежит в OneDrive, баги лучше хранить в обычной локальной папке (например `C:\docker\ros2_ws`) — OneDrive иногда синхронизирует файлы не полностью, и баг не откроется.

## 4. Сборка и запуск

### Первый раз (сборка, 10–20 минут)

Открой PowerShell в папке проекта:
```powershell
cd C:\hakaton\mgts
docker compose --profile pc up -d --build
```
Docker скачает пакеты ROS и соберёт образ — это нормально, что долго.

### Каждый следующий раз

```powershell
cd C:\hakaton\mgts
docker compose --profile pc up -d
```

### Вход в контейнер

```powershell
docker exec -it r_hacatonius bash -l
```

> Флаг `-l` обязателен: без него команды `ros2`/`rviz2` не будут найдены.

Промпт сменится на `root@...:/ros2_ws#` — ты внутри контейнера.

## 5. Проигрывание бага в RViz

Внутри контейнера:

```bash
# 1. Убедись, что баг виден (путь с учётом вложенности!)
ls /ros2_ws
ros2 bag info /ros2_ws/bag_for_mapping/bag_for_mapping

# 2. Запуск
/opt/go2_playback/play_viz.sh /ros2_ws/bag_for_mapping/bag_for_mapping
```

Откроется окно RViz с облаком лидара, зелёной линией одометрии и осями координат.

**Управление воспроизведением** (в терминале, где запущен скрипт):
- `Пробел` — пауза / продолжить
- `↑` / `↓` — скорость ±10%
- `→` — следующее сообщение

**Чтобы баг крутился по кругу** (не останавливался после окончания записи):
```bash
ros2 bag play /ros2_ws/bag_for_mapping/bag_for_mapping --clock 100 --loop &
rviz2 -d /opt/go2_playback/go2.rviz --ros-args -p use_sim_time:=true
```

**Просмотр с других ракурсов** (в окне RViz):
- Левая кнопка мыши + движение — вращение
- Правая кнопка / колёсико — приближение
- Средняя кнопка (или Shift + левая) — сдвиг

## 6. Добавление новых багов

Положи папку нового бага в `ros2_ws` на Windows — она сразу доступна в контейнере по пути `/ros2_ws/<имя>`. Контейнер пересобирать не нужно.

## 7. Разработка своих решений

Внутри контейнера (окружение ROS 2 Humble уже настроено):

```bash
# Создать пакет (Python или C++)
ros2 pkg create --build-type ament_python my_solution /ros2_ws/src/my_solution
# ros2 pkg create --build-type ament_cmake my_solution /ros2_ws/src/my_solution

# Собрать
cd /ros2_ws && colcon build --symlink-install

# Запустить свою ноду на данных бага
ros2 bag play /ros2_ws/bag_for_mapping/bag_for_mapping &
ros2 run my_solution my_node
```

В образе уже установлены: nav2, slam-toolbox, robot-localization, pcl-ros и инструменты сборки. Исходники пишутся в `ros2_ws/src` — они видны и редактируются с Windows (открывай папку в VS Code, PyCharm и т.п.).

## 8. Остановка и выход

- Выход из контейнера: `exit` (контейнер продолжит работать в фоне)
- Остановить контейнер (в PowerShell, из папки проекта):
  ```powershell
  docker compose --profile pc down
  ```
- Баги и исходники в `ros2_ws` при этом **не удаляются** — они лежат на твоём диске

## 9. Возможные проблемы

| Проблема | Решение |
|---|---|
| `The term 'docker' is not recognized` | Закрой и открой PowerShell заново; убедись, что Docker Desktop запущен (зелёный статус) |
| Ошибка про `Virtual Machine Platform` | Выполни шаг 2.1 — компонент Windows не включён |
| `device or resource busy` в Docker Desktop | Выйди из Docker Desktop (трей → Quit), выполни `wsl --shutdown`, запусти Docker заново |
| Окно RViz не появляется, `couldn't open display` | Запусти VcXsrv заново с галочкой «Disable access control»; проверь, что иконка X в трее есть; разреши VcXsrv в брандмауэре |
| RViz открылся, но пусто и не реагирует на мышь | Баг доиграл и остановился — перезапусти его с `--loop` (см. шаг 5). Проверка: `ros2 topic echo /clock --once` — если «висит», баг не играет |
| `ros2: command not found` внутри контейнера | Заходи с флагом `-l`: `docker exec -it r_hacatonius bash -l` |
| `Could not find metadata in bag directory` | Путь к багу должен вести в самую глубокую папку (там, где `metadata.yaml`). Подсмотри точный путь: `find /ros2_ws -name metadata.yaml` |
| В списке топиков RViz (Add → By Topic) пусто | Баг не проигрывается — запусти его отдельно с `--loop`, подожди 5–10 секунд |
| `No storage could be initialized` | Баг скопировался не полностью (типично для OneDrive) — перекопируй папку бага заново |
| Скрипт ругается на `$'\r'` | Файл сохранён с Windows-окончаниями строк — используй версию из образа: `/opt/go2_playback/play_viz.sh` |

## 10. Где что лежит

| Что | Где |
|---|---|
| Баги (читаешь/пишешь) | `ros2_ws` на Windows ↔ `/ros2_ws` в контейнере |
| Скрипт проигрывания | `/opt/go2_playback/play_viz.sh` |
| Конфиг RViz | `/opt/go2_playback/go2.rviz` |
| Сообщения Unitree (`/lowstate` и др.) | `/opt/unitree_msgs` |
| ROS 2 Humble | `/opt/ros/humble` |
