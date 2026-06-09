import pygame
import math
import random
import os

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("В тылу врага: Тактическая операция")
clock = pygame.time.Clock()

# --- ЦВЕТА ---
BACKGROUND = (20, 25, 30)
PATH_COLOR = (0, 255, 255)
MINE_COLOR = (255, 30, 30)
STATION_COLOR = (100, 100, 250)
TEXT_COLOR = (255, 255, 255)
ENEMY_COLOR = (255, 130, 0)
GRID_COLOR = (30, 45, 55)
START_COLOR = (0, 220, 0)

# --- СТАНЦИИ ---
STATIONS = [
    [100, 150], [700, 150], [100, 450], [700, 450]
]

# --- ИГРОВЫЕ ПЕРЕМЕННЫЕ ---
score = 0
level = 1
mines_per_level = 2

show_rules = True
game_over = False
is_moving = False

start_station_idx = random.randint(0, 3)
end_station_idx = random.randint(0, 3)
while end_station_idx == start_station_idx:
    end_station_idx = random.randint(0, 3)

control_points = []
evaluated_path = []
animation_tick = 0.0

current_idx = 0.0
DRONE_SPEED = 3.5

enemy_pos = [400, 300]
enemy_angle = 0.0
enemy_speed = 0.025

mines = []
particles = []

# Загрузка картинки фона
bg_image = None
if os.path.exists("battle_map.png"):
    try:
        bg_image = pygame.image.load("battle_map.png").convert()
        bg_image = pygame.transform.scale(bg_image, (WIDTH, HEIGHT))
    except Exception as e:
        print("Ошибка загрузки фона:", e)


def generate_mines(count):
    global mines
    mines.clear()
    for _ in range(count):
        while True:
            mx, my = random.randint(40, 760), random.randint(40, 560)
            near_station = False
            for st in STATIONS:
                if math.sqrt((mx - st[0]) ** 2 + (my - st[1]) ** 2) < 70:
                    near_station = True
            if not near_station:
                mines.append([mx, my])
                break


generate_mines(mines_per_level * level)


# --- МАТЕМАТИКА БЕЗЬЕ ---
def evaluate_bezier(p0, p1, p2, p3, t):
    b0 = (1 - t) ** 3
    b1 = 3 * ((1 - t) ** 2) * t
    b2 = 3 * (1 - t) * (t ** 2)
    b3 = t ** 3
    return [
        int(b0 * p0[0] + b1 * p1[0] + b2 * p2[0] + b3 * p3[0]),
        int(b0 * p0[1] + b1 * p1[1] + b2 * p2[1] + b3 * p3[1])
    ]


def build_bezier_path():
    global evaluated_path, current_idx
    evaluated_path.clear()
    current_idx = 0.0

    if len(control_points) == 4:
        approx_length = 0.0
        prev_pt = control_points[0]
        for step in range(1, 21):
            t = step / 20.0
            pt = evaluate_bezier(control_points[0], control_points[1], control_points[2], control_points[3], t)
            approx_length += math.sqrt((pt[0] - prev_pt[0]) ** 2 + (pt[1] - prev_pt[1]) ** 2)
            prev_pt = pt

        steps = max(15, int(approx_length / DRONE_SPEED))

        for step in range(steps + 1):
            pt = evaluate_bezier(control_points[0], control_points[1], control_points[2], control_points[3],
                                 step / float(steps))
            evaluated_path.append(pt)


# --- СИСТЕМА ЧАСТИЦ ВЗРЫВА ---
def create_explosion(pos):
    global particles
    particles.clear()
    for _ in range(25):
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1.5, 5.0)
        p_vel = [math.cos(angle) * speed, math.sin(angle) * speed]
        p_color = random.choice([(255, 40, 40), (255, 130, 0), (255, 220, 0)])
        p_radius = random.randint(4, 7)
        p_life = random.randint(25, 50)

        particles.append({
            "pos": list(pos),
            "vel": p_vel,
            "color": p_color,
            "radius": p_radius,
            "max_life": p_life,
            "life": p_life
        })


# --- ФУНКЦИЯ ОТРИСОВКИ ПРОЦЕДУРНОГО СОЛДАТА ---
def draw_soldier(surface, pos, tick, walking):
    x, y = pos

    shadow_surf = pygame.Surface((24, 12), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 120), (0, 0, 24, 12))
    surface.blit(shadow_surf, (x - 12, y + 16))

    if walking:
        swing = math.sin(tick * 1.5) * 12
        bobbing = abs(math.cos(tick * 3.0)) * 3
    else:
        swing = 0
        bobbing = math.sin(tick * 0.4) * 1

    y_body = y - int(bobbing)

    # Ноги
    pygame.draw.line(surface, (50, 60, 45), (x - 4, y_body + 4), (x - 5 + int(swing), y + 18), 4)
    pygame.draw.circle(surface, (20, 20, 20), (x - 5 + int(swing), y + 18), 3)
    pygame.draw.line(surface, (50, 60, 45), (x + 4, y_body + 4), (x + 5 - int(swing), y + 18), 4)
    pygame.draw.circle(surface, (20, 20, 20), (x + 5 - int(swing), y + 18), 3)

    # Торс
    pygame.draw.rect(surface, (70, 85, 60), (x - 7, y_body - 12, 14, 18))
    pygame.draw.rect(surface, (40, 50, 35), (x - 6, y_body - 10, 12, 13))

    # Руки
    pygame.draw.line(surface, (70, 85, 60), (x - 7, y_body - 10), (x - 11 - int(swing * 0.5), y_body + 2), 3)
    pygame.draw.line(surface, (70, 85, 60), (x + 7, y_body - 10), (x + 11 + int(swing * 0.5), y_body + 2), 3)

    # Голова и каска
    pygame.draw.circle(surface, (210, 170, 135), (x, y_body - 17), 5)
    pygame.draw.arc(surface, (45, 55, 40), (x - 6, y_body - 23, 12, 10), 0, math.pi, 4)
    pygame.draw.line(surface, (30, 30, 30), (x - 6, y_body - 18), (x + 6, y_body - 18), 1)


# --- ФУНКЦИЯ ОТРИСОВКИ ВРАЖЕСКОГО ДРОНА ---
def draw_enemy_drone(surface, pos, tick):
    x, y = pos
    length = 16

    shadow_surf = pygame.Surface((20, 10), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (0, 0, 20, 10))
    surface.blit(shadow_surf, (x - 6, y + 40))

    pygame.draw.line(surface, (60, 65, 70), (x - length, y - length), (x + length, y + length), 3)
    pygame.draw.line(surface, (60, 65, 70), (x + length, y - length), (x - length, y + length), 3)

    offsets = [(-length, -length), (length, -length), (-length, length), (length, length)]
    for ox, oy in offsets:
        rot_x = int(math.cos(tick * 2.0) * 8)
        rot_y = int(math.sin(tick * 2.0) * 8)
        pygame.draw.line(surface, ENEMY_COLOR, (x + ox - rot_x, y + oy - rot_y), (x + ox + rot_x, y + oy + rot_y), 2)
        pygame.draw.circle(surface, (40, 40, 40), (x + ox, y + oy), 3)

    pygame.draw.circle(surface, (40, 45, 50), (x, y), 10)
    eye_flash = int(127 + math.sin(tick * 4) * 127)
    pygame.draw.circle(surface, (eye_flash, 0, 0), (x, y), 4)


# --- ГЛАВНЫЙ ЦИКЛ ИГРЫ ---
running = True
while running:
    if bg_image:
        screen.blit(bg_image, (0, 0))
    else:
        screen.fill(BACKGROUND)
        for x in range(0, WIDTH, 40):
            pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, 40):
            pygame.draw.line(screen, GRID_COLOR, (0, y), (WIDTH, y), 1)
        pygame.draw.circle(screen, (35, 50, 60), (400, 300), 200, 1)

    animation_tick += 0.12

    # 1. ОБРАБОТКА ВВОДА
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if show_rules and event.key == pygame.K_SPACE:
                show_rules = False
            if event.key == pygame.K_r:
                score, level = 0, 1
                game_over = False
                is_moving = False
                show_rules = False
                control_points.clear()
                evaluated_path.clear()
                particles.clear()
                current_idx = 0.0
                enemy_angle = 0.0
                generate_mines(mines_per_level * level)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not show_rules and not game_over and not is_moving:
            control_points.append(list(event.pos))

            if len(control_points) == 2:
                p0 = STATIONS[start_station_idx]
                p1 = control_points[0]
                p2 = control_points[1]
                p3 = STATIONS[end_station_idx]

                control_points = [p0, p1, p2, p3]
                build_bezier_path()
                is_moving = True

    # 2. ИГРОВАЯ ЛОГИКА
    if not show_rules:
        if not game_over:
            enemy_angle += enemy_speed
            enemy_pos[0] = int(400 + math.cos(enemy_angle) * 170)
            enemy_pos[1] = int(300 + math.sin(enemy_angle) * 140)
        if is_moving and not game_over:
            idx_int = min(int(current_idx), len(evaluated_path) - 1)
            robot_pos = evaluated_path[idx_int]

            speed_modifier = 1.0

            if bg_image:
                cx = max(0, min(WIDTH - 1, robot_pos[0]))
                cy = max(0, min(HEIGHT - 1, robot_pos[1]))
                r, g, b, *a = bg_image.get_at((cx, cy))

                if b > r and b > 100:
                    speed_modifier = 0.5
                elif r > 135 and g > 150:
                    speed_modifier = 1.4

            current_idx += speed_modifier

            if int(current_idx) >= len(evaluated_path):
                score += 1
                level += 1
                current_idx = 0.0
                is_moving = False
                control_points.clear()
                evaluated_path.clear()

                start_station_idx = end_station_idx
                while end_station_idx == start_station_idx:
                    end_station_idx = random.randint(0, 3)

                generate_mines(mines_per_level * level)
            else:
                # Проверка коллизий с минами
                for mine in mines:
                    if math.sqrt((robot_pos[0] - mine[0]) ** 2 + (robot_pos[1] - mine[1]) ** 2) < 18:
                        game_over = True
                        is_moving = False
                        create_explosion(robot_pos)

                        # Проверка коллизий с патрулем
                if math.sqrt((robot_pos[0] - enemy_pos[0]) ** 2 + (robot_pos[1] - enemy_pos[1]) ** 2) < 32:
                    game_over = True
                    is_moving = False
                    create_explosion(robot_pos)

    # 3. ОТРИСОВКА ЭКРАНОВ
    if show_rules:
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill((10, 15, 20))
        overlay.set_alpha(230)
        screen.blit(overlay, (0, 0))

        font_title = pygame.font.SysFont("Arial", 36, bold=True)
        font_text = pygame.font.SysFont("Arial", 20)

        title_surf = font_title.render("ТАКТИЧЕСКИЙ ИНСТРУКТАЖ", True, PATH_COLOR)
        screen.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, 80)))

        rules = [
            "1. Ваша цель — безопасно провести разведчика между точками сбора.",
            "2. Зеленый маркер — СТАРТ, Желтый маркер — ТОЧКА НАЗНАЧЕНИЯ.",
            "3. Кликните ЛКМ ровно 2 РАЗА по карте, чтобы проложить скрытный маршрут.",
            "4. Солдат автоматически выдвинется по рассчитанной кривой Безье.",
            "5. Скорость зависит от рельефа: река замедляет, сухая трава ускоряет.",
            "6. Опасайтесь светящихся красных МИН и вражеского дрона-ПАТРУЛЯ.",
        ]

        y_offset = 180
        for rule in rules:
            rule_surf = font_text.render(rule, True, TEXT_COLOR)
            screen.blit(rule_surf, rule_surf.get_rect(center=(WIDTH // 2, y_offset)))
            y_offset += 40

        start_surf = font_title.render("Нажмите ПРОБЕЛ для начала операции!", True, START_COLOR)
        screen.blit(start_surf, start_surf.get_rect(center=(WIDTH // 2, 480)))

    elif game_over:
        font_go = pygame.font.SysFont("Arial", 46, bold=True)
        font_res = pygame.font.SysFont("Arial", 28)

        go_surf = font_go.render("ОПЕРАЦИЯ ПРОВАЛЕНА!", True, MINE_COLOR)
        screen.blit(go_surf, go_surf.get_rect(center=(WIDTH // 2, 200)))

        res_surf = font_res.render(f"Ваш результат — {score} выполненных миссий", True, TEXT_COLOR)
        screen.blit(res_surf, res_surf.get_rect(center=(WIDTH // 2, 280)))

        hint_surf = font_res.render("Нажмите R, чтобы запросить подкрепление", True, PATH_COLOR)
        screen.blit(hint_surf, hint_surf.get_rect(center=(WIDTH // 2, 350)))

        # Рендер частиц взрыва
        for p in particles[:]:
            p["pos"][0] += p["vel"][0]
            p["pos"][1] += p["vel"][1]
            p["life"] -= 1

            ratio = p["life"] / p["max_life"]
            if ratio > 0:
                current_rad = max(1, int(p["radius"] * ratio))
                p_surf = pygame.Surface((current_rad * 2, current_rad * 2), pygame.SRCALPHA)
                alpha = int(255 * ratio)
                pygame.draw.circle(p_surf, (p["color"][0], p["color"][1], p["color"][2], alpha),
                                   (current_rad, current_rad), current_rad)
                screen.blit(p_surf, (int(p["pos"][0] - current_rad), int(p["pos"][1] - current_rad)))

            if p["life"] <= 0:
                particles.remove(p)

    else:
        # Станции
        for idx, st in enumerate(STATIONS):
            if idx == start_station_idx:
                color = (0, 255, 0)
            elif idx == end_station_idx:
                color = (255, 255, 0)
            else:
                color = STATION_COLOR
            pygame.draw.circle(screen, color, st, 25)
            pygame.draw.circle(screen, TEXT_COLOR, st, 25, 2)
            font_st = pygame.font.SysFont("Arial", 16, bold=True)
            screen.blit(font_st.render(f"Пункт {idx}", True, TEXT_COLOR), (st[0] - 28, st[1] - 45))

        # Мины
        mine_glow = int(120 + math.sin(animation_tick * 4.0) * 100)
        for mine in mines:
            glow_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 0, 0, mine_glow // 4), (15, 15), 14, 1)
            screen.blit(glow_surf, (mine[0] - 15, mine[1] - 15))

            pygame.draw.circle(screen, (255, 50, 50), mine, 5)
            pygame.draw.circle(screen, (255, 255, 200), mine, 2)

        # Патруль
        draw_enemy_drone(screen, enemy_pos, animation_tick)
        font_enemy = pygame.font.SysFont("Arial", 11, bold=True)
        enemy_surf = font_enemy.render("ВРАЖЕСКИЙ ДРОН", True, ENEMY_COLOR)
        screen.blit(enemy_surf, enemy_surf.get_rect(center=(enemy_pos[0], enemy_pos[1] - 26)))

        # Траектория Безье
        if len(evaluated_path) > 1:
            for i in range(len(evaluated_path) - 1):
                pygame.draw.line(screen, PATH_COLOR, evaluated_path[i], evaluated_path[i + 1], 3)

        if len(control_points) == 1:
            pygame.draw.line(screen, (100, 100, 100), STATIONS[start_station_idx], control_points[0], 1)
            pygame.draw.circle(screen, (255, 255, 255), control_points[0], 5)

        # Солдат
        if is_moving:
            idx_int = min(int(current_idx), len(evaluated_path) - 1)
            draw_soldier(screen, evaluated_path[idx_int], animation_tick, True)
        else:
            draw_soldier(screen, STATIONS[start_station_idx], animation_tick, False)

        # HUD (Интерфейс игры по левому краю)
        ui_font = pygame.font.SysFont("Arial", 20)
        screen.blit(ui_font.render(f"УСПЕШНО: {score}  |  УРОВЕНЬ УГРОЗЫ: {level}", True, TEXT_COLOR), (20, 20))
        task_text = f"ПРИКАЗ: Выдвинуться из Пункта {start_station_idx} в Пункт {end_station_idx}"
        screen.blit(ui_font.render(task_text, True, (255, 255, 0)), (20, 50))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()