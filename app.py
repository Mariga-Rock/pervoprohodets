import random
import pickle
import json
from flask import Flask, request, render_template, session, redirect, url_for

# ============================ КЛАССЫ ДЛЯ НОВЫХ СУЩНОСТЕЙ ============================

class Traveler:
    """Расширенный класс путешественника с чертами"""
    def __init__(self, name):
        self.name = name
        self.hunting = random.randint(3, 7)
        self.endurance = random.randint(3, 7)
        self.alive = True
        self.scurvy = False
        # Новые черты (вероятность 10% для каждой)
        self.is_doctor = random.random() < 0.1
        self.is_scientist = random.random() < 0.1
        # Для учёта травм
        self.injured_until_season = -1  # -1 = здоров
        self.injured_with = None  # кто ухаживает

class City:
    """Класс для представления города / поселения"""
    def __init__(self, name, river=None):
        self.name = name
        self.river = river or random.choice(["Обь", "Енисей", "Лена", "Иртыш", "Амур"])
        self.population = random.randint(50, 200)
        self.has_church = False
        self.has_hospital = False
        self.has_blacksmith = False
        self.has_iron_mine = False
        self.has_silver_mine = False
        self.is_frontier = False  # пограничная застава (Китай)
        self.trade_bonus = 0      # чайная торговля

class Achievement:
    """Система долгосрочных целей"""
    GOALS = [
        {"id": "first_city", "name": "Основать первый город", "reward": "бонус к обороне"},
        {"id": "fur_1000", "name": "Добыть 1000 пушнины", "reward": "доступ к царскому двору"},
        {"id": "artifacts_5", "name": "Найти 5 артефактов", "reward": "+5% к добыче"},
        {"id": "cure_all", "name": "Вылечить всех больных цингой", "reward": "повышение морали"},
    ]

    def __init__(self):
        self.completed = set()

    def check_and_reward(self, game):
        s = game.settlement
        # Проверка условий
        if not self.is_completed("first_city") and len(s.cities) >= 1:
            self.complete("first_city", game, "🏙️ Ты основал первый город! Отныне разбойники будут реже нападать.")
            s.bandit_modifier = 0.5  # снижаем шанс нападений
        if not self.is_completed("fur_1000") and s.total_fur_sent_to_tsar >= 1000:
            self.complete("fur_1000", game, "👑 Ты отправил 1000 пушнины в казну! Царь приглашает тебя в свой двор.")
            game.court_access = True
        if not self.is_completed("artifacts_5") and s.artifacts_found >= 5:
            self.complete("artifacts_5", game, "🔮 Ты собрал 5 древних артефактов! Добыча пушнины увеличена на 5%.")
            s.hunting_bonus_permanent = 1.05
        if not self.is_completed("cure_all") and s.count_scurvy() == 0 and game.total_cases_scurvy > 0:
            self.complete("cure_all", game, "💚 Ты вылечил всех от цинги! Мораль отряда повышена.")
            s.morale_bonus = 1.1

    def is_completed(self, goal_id):
        return goal_id in self.completed

    def complete(self, goal_id, game, message):
        self.completed.add(goal_id)
        game.add_message(message)
        game.add_message("🏆 Достижение разблокировано!")

# ============================ ОСНОВНЫЕ КЛАССЫ ============================

class Settlement:
    def __init__(self):
        self.travelers = [Traveler("Ермак"), Traveler("Иван")]
        self.fur = 0
        self.equipment = 0
        self.money = 350
        self.dogs = 0
        self.horses = 0
        self.lands = 1
        self.charters = 0
        self.total_charters_earned = 0
        self.cabbage = 0
        self.church = False
        self.palisade = False
        self.year = 1
        self.season = 0
        self.total_fur_sent_to_tsar = 0
        self.penalty_next_season = 0
        self.turn = 0
        self.city_names = []   # для обратной совместимости
        self.last_offer_level = 0
        self.patron_of_science = False
        self.benefactor = False

        # НОВЫЕ ПОЛЯ
        self.cities = []          # список объектов City
        self.iron_deposits = []   # названия городов с рудой
        self.silver_deposits = []
        self.has_ancient_maps = False
        self.map_bonus = 0
        self.maps_created = 0     # учёт карт для учёных
        self.artifacts_found = 0
        self.hunting_bonus_permanent = 1.0
        self.morale_bonus = 1.0
        self.bandit_modifier = 1.0
        self.court_access = False
        self.noble_title = None   # 'дворянин' или 'вельможа'
        self.injured_travelers = []  # список кортежей (имя, сезонов_осталось, сопровождающий)
        self.tutorial_step = 0
        self.difficulty_modifier = 1.0
        self.leaderboard = []     # (имя, грамоты, города)

    def total_animals(self):
        return self.dogs + self.horses

    def max_travelers(self):
        return len(self.travelers)

    def living_travelers(self):
        """Возвращает здоровых и не травмированных путешественников"""
        result = []
        for t in self.travelers:
            if t.alive and t.injured_until_season == -1:
                result.append(t)
        return result

    def all_alive(self):
        """Все живые (включая травмированных)"""
        return [t for t in self.travelers if t.alive]

    def count_scurvy(self):
        return sum(1 for t in self.travelers if t.alive and t.scurvy)

    def has_scurvy(self):
        return self.count_scurvy() > 0

    def remove_dead(self):
        self.travelers = [t for t in self.travelers if t.alive]

    def add_traveler(self, name="Новобранец"):
        if self.money >= 50:
            self.money -= 50
            new_t = Traveler(name)
            self.travelers.append(new_t)
            return True
        return False

class Game:
    def __init__(self):
        self.settlement = Settlement()
        self.running = True
        self.merchant_price = 5
        self.bandit_activity = 0.2
        self.event_manager = EventManager(self)
        self.messages = []
        self.awaiting_input = False
        self.input_prompt = ""
        self.input_callback = None
        self.pending_command = None
        self._charter_level = 0
        self._bandit_count = 0
        self._bandit_living = []
        self._bandit_fur_gained = 0
        self.current_image_index = random.randint(1, 3)
        self.achievements = Achievement()
        self.court_access = False
        self.total_cases_scurvy = 0   # для достижения
        self.hunting_boost = False    # от шамана
        self.hunting_boost_multiplier = 1.0
        self.tutorial_messages_shown = set()
        self.difficulty_adaptation_counter = 0
        self.china_discovered = False

    def add_message(self, text):
        self.messages.append(text)

    def set_input_callback(self, callback, prompt):
        self.awaiting_input = True
        self.input_prompt = prompt
        self.input_callback = callback
        self.add_message(prompt)

    def advance_image(self):
        self.current_image_index = (self.current_image_index % 3) + 1

    # -------------------- НОВЫЕ МЕТОДЫ ДЛЯ ДИНАМИЧЕСКОЙ СЛОЖНОСТИ --------------------
    def adjust_difficulty(self):
        s = self.settlement
        # Если игрок часто проигрывает (смерти, долги) - облегчаем
        if len([t for t in s.travelers if not t.alive]) > 2:
            s.difficulty_modifier = max(0.8, s.difficulty_modifier - 0.05)
        if s.money < -50:
            s.difficulty_modifier = max(0.7, s.difficulty_modifier - 0.1)
        # Если слишком успешен - усложняем
        if s.charters > 10 and s.lands > 5:
            s.difficulty_modifier = min(1.3, s.difficulty_modifier + 0.05)
        # Ограничим диапазон
        s.difficulty_modifier = max(0.6, min(1.4, s.difficulty_modifier))

    # -------------------- ИНТЕРАКТИВНЫЕ ПОДСКАЗКИ --------------------
    def tutorial_advice(self):
        s = self.settlement
        step = s.tutorial_step
        if step == 0 and s.season == 1 and len(s.living_travelers()) == 2:
            self.add_message("💡 Подсказка: Лето — лучшее время для экспедиций. Попробуй отправить отряд! (команда 'отправить')")
            s.tutorial_step = 1
        elif step == 1 and s.fur > 0 and s.season == 2:
            self.add_message("💡 Подсказка: Осенью можно продать пушнину. Введи 'продать пушнину <количество>'.")
            s.tutorial_step = 2
        elif step == 2 and s.equipment < 5 and s.money > 20:
            self.add_message("💡 Подсказка: У тебя мало экипировки. Купи её командой 'купить экипировку <количество>' (5 руб/ед).")
            s.tutorial_step = 3
        elif step == 3 and s.season == 3 and s.cabbage == 0:
            self.add_message("💡 Подсказка: Зима близко! Запасись квашеной капустой осенью, чтобы избежать голода.")
            s.tutorial_step = 4
        # Дополнительные подсказки при появлении новых механик
        if len(s.cities) == 1 and not self.has_shown_tutorial("city"):
            self.add_message("💡 Подсказка: Ты основал город! В нём можно построить храм и лечебницу, если есть врач.")
            self.mark_tutorial_shown("city")
        if s.charters >= 5 and not self.has_shown_tutorial("charter"):
            self.add_message("💡 Подсказка: У тебя 5 грамот! Теперь можно основать город (команда 'основать город <название>').")
            self.mark_tutorial_shown("charter")

    def has_shown_tutorial(self, key):
        return key in self.tutorial_messages_shown

    def mark_tutorial_shown(self, key):
        self.tutorial_messages_shown.add(key)

    # -------------------- ОБРАБОТКА КОМАНД (дополнена) --------------------
    def process_command(self, cmd):
        self.messages = []
        if self.awaiting_input:
            self.awaiting_input = False
            if self.input_callback:
                self.input_callback(cmd)
            self.advance_image()
            return self.messages

        if not cmd:
            self.add_message("Введите команду.")
            self.advance_image()
            return self.messages

        parts = cmd.strip().split()
        action = parts[0]
        args = parts[1:]

        cmd_map = {
            'отправить': self.cmd_expedition,
            'продать пушнину': self.cmd_sell,
            'послать пушнину в царскую казну': self.cmd_give_to_tsar,
            'купить экипировку': self.cmd_buy_equipment,
            'купить собаку': self.cmd_buy_dog,
            'купить лошадь': self.cmd_buy_horse,
            'купить капусту': self.cmd_buy_cabbage,
            'построить храм': self.cmd_build_church,
            'построить частокол': self.cmd_build_palisade,
            'подкупить разбойников': self.cmd_bribe_bandits,
            'отправить семье': self.cmd_send_money_to_family,
            'основать город': self.cmd_found_city,
            'пожертвовать науке': self.cmd_donate_science,
            'пожертвовать сирым': self.cmd_donate_charity,
            'статус': self.cmd_status,
            'следующий сезон': self.cmd_skip,
            'пропустить год': self.cmd_skip_year,
            'помощь': self.cmd_help,
            'выход': self.cmd_quit,
            'построить кузницу': self.cmd_build_blacksmith,
            'продать экипировку': self.cmd_sell_equipment,
            'города': self.cmd_show_cities,
            'лидеры': self.cmd_show_leaderboard,
        }

        matched = None
        for key in sorted(cmd_map.keys(), key=len, reverse=True):
            if cmd == key or cmd.startswith(key + ' '):
                matched = key
                break
        if matched:
            args = cmd[len(matched):].strip().split()
            try:
                cmd_map[matched](args)
            except Exception as e:
                self.add_message(f"Ошибка: {e}")
        else:
            self.add_message("Неизвестная команда. Введите 'помощь'.")

        self.after_action()
        self.advance_image()
        return self.messages

    def after_action(self):
        self.check_debt()
        self.heal_scurvy_with_cabbage()
        s = self.settlement
        # Проверка достижений
        self.achievements.check_and_reward(self)
        # Подсказки
        self.tutorial_advice()
        # Динамическая сложность
        self.adjust_difficulty()
        # Обработка травм (уменьшаем счётчики)
        self.process_injuries()
        # Рост населения городов
        for city in s.cities:
            city.population += random.randint(0, 3)
        # Проверка на 5 грамот (основание города)
        if s.charters >= 5:
            current_level = s.charters // 5
            if current_level > s.last_offer_level:
                self.offer_charter_choice()
        # Проверка на дворянские звания
        if s.total_fur_sent_to_tsar >= 1000 and s.noble_title is None:
            s.noble_title = 'дворянин'
            self.add_message("👑 Царь жалует тебе дворянское звание за твои заслуги! Ты теперь дворянин.")
        if s.total_fur_sent_to_tsar >= 10000 and s.noble_title != 'вельможа':
            s.noble_title = 'вельможа'
            self.add_message("👑 Великая честь! Ты стал вельможей! Но помни: с большим богатством приходит и большая ответственность.")
        # Проверка на пьянство (уже есть)

    # -------------------- ОБРАБОТКА ТРАВМ --------------------
    def process_injuries(self):
        s = self.settlement
        new_injured = []
        for entry in s.injured_travelers:
            name, seasons_left, caretaker = entry
            seasons_left -= 1
            if seasons_left <= 0:
                # Возвращаем в строй
                for t in s.travelers:
                    if t.name == name and t.alive:
                        t.injured_until_season = -1
                        self.add_message(f"💚 {name} полностью оправился от травмы и вернулся в отряд!")
                        # сопровождающий тоже возвращается
                        if caretaker:
                            for c in s.travelers:
                                if c.name == caretaker and c.alive:
                                    c.injured_until_season = -1
                                    self.add_message(f"💚 {caretaker} вернулся в отряд после ухода за больным.")
                        break
            else:
                new_injured.append((name, seasons_left, caretaker))
        s.injured_travelers = new_injured

    # -------------------- КОМАНДЫ (дополненные и новые) --------------------
    def cmd_help(self, args):
        self.add_message(self.get_help_text())

    def get_help_text(self):
        return """
Список команд:
  отправить [кол-во] [регион]          – экспедиция (только летом). По умолчанию – все на первую территорию.
  отправить новый                       – исследовать новую территорию (все путешественники).
  продать пушнину <кол-во>             – продать пушнину (только осенью). Цена зависит от запасов.
  послать пушнину в царскую казну <кол-во> – за 100 пушнины даётся 1 грамота.
  купить экипировку <кол-во>           – купить экипировку (5 руб/ед, с кузницей – дешевле).
  купить собаку [кол-во]               – купить собак (50 руб/шт).
  купить лошадь [кол-во]               – купить лошадей (50 руб/шт).
  купить квашеную капусту <кол-во>     – только осенью (10 руб/ед).
  построить храм                       – построить храм в текущем городе (500 руб).
  построить частокол                   – защита от разбойников (100 руб).
  построить кузницу                    – если есть железная руда в городе (требует 200 руб).
  подкупить разбойников <сумма>        – снизить активность.
  отправить семье <сумма>              – отправить деньги.
  основать город <название>            – основать город (5+5*число_городов грамот).
  пожертвовать науке <сумма>           – стать меценатом.
  пожертвовать сирым <сумма>           – стать благотворителем.
  статус                               – показать состояние.
  следующий сезон                      – перейти к следующему сезону.
  пропустить год                       – пропустить год (50 руб + 2 капусты).
  помощь                               – показать эту справку.
  города                               – показать информацию о городах.
  лидеры                               – таблица лидеров.
  выход                                – выйти.

Новые возможности:
  - Учёные составляют карты (каждые 3 карты = 1 грамота).
  - Врачи помогают при травмах, могут открыть лечебницу в городе.
  - Месторождения руды и серебра позволяют строить кузницы и получать доход.
  - Встречи с племенами дают выбор: обряд удачи или обращение в православие.
  - Достижения открывают постоянные бонусы.
  - При 1000 пушнины – дворянство, при 10000 – вельможа.
  - Граница с Китаем (шанс 4%) открывает чайную торговлю.
        """

    # ... (остальные команды из предыдущей версии, но с изменениями)

    def cmd_status(self, args):
        self.display_status()

    def display_status(self):
        s = self.settlement
        season_names = ["🌸 Весна", "☀️ Лето", "🍂 Осень", "❄️ Зима"]
        self.add_message("\n" + "-"*50)
        self.add_message(f"Год {s.year}, сезон: {season_names[s.season]}")
        self.add_message(f"Путешественников: {len(s.living_travelers())} (всего {len(s.all_alive())})")
        if s.count_scurvy() > 0:
            self.add_message(f"   (Цинга: {s.count_scurvy()} больных)")
        self.add_message(f"Пушнина: {s.fur} | Экипировка: {s.equipment} | Деньги: {s.money} руб.")
        self.add_message(f"Собаки/лошади: {s.dogs}/{s.horses} (всего {s.total_animals()})")
        self.add_message(f"Открытые земли: {s.lands} | Царские грамоты: {s.charters}")
        if s.cities:
            self.add_message(f"Городов: {len(s.cities)}")
        if s.has_ancient_maps:
            self.add_message("🗺️ У тебя есть древние карты (+1 к открытию новых земель)")
        if s.maps_created > 0:
            self.add_message(f"🗺️ Составлено карт: {s.maps_created} (каждые 3 дают грамоту)")
        if s.noble_title:
            self.add_message(f"👑 Титул: {s.noble_title}")
        if s.court_access:
            self.add_message("🏛️ Доступ к царскому двору")
        if s.patron_of_science:
            self.add_message("🔬 Меценат")
        if s.benefactor:
            self.add_message("❤️ Благотворитель")
        if s.penalty_next_season > 0:
            self.add_message(f"⚠️ Штраф к добыче: -{s.penalty_next_season}%")
        if s.season == 2:
            price_mod = self.get_fur_price_modifier()
            self.add_message(f"💰 Цена пушнины у купцов: {self.merchant_price * price_mod:.1f} руб./ед. (можно продавать)")
        self.add_message("-"*50)

    # -------------------- НОВАЯ ЛОГИКА ДЛЯ ЦЕН НА ПУШНИНУ --------------------
    def get_fur_price_modifier(self):
        s = self.settlement
        # чем больше пушнины, тем ниже цена (от 0.5 до 1.0)
        return max(0.5, 1 - (s.fur / 5000))

    # -------------------- КОМАНДА ОТПРАВИТЬ (с учётом новых механик) --------------------
    def cmd_expedition(self, args):
        if self.settlement.season != 1:
            self.add_message("❌ Экспедиции возможны только летом!")
            return
        s = self.settlement
        living = s.living_travelers()
        if not living:
            self.add_message("Нет здоровых путешественников.")
            return

        # Парсинг аргументов
        count = len(living)
        region = '1'
        is_new = False

        if args:
            first = args[0]
            if first == 'новый':
                is_new = True
                region = 'новый'
                if len(args) > 1:
                    # может быть указано количество
                    try:
                        count = int(args[1])
                    except:
                        pass
            elif first.isdigit():
                count = int(first)
                if count <= 0:
                    self.add_message("Количество должно быть положительным.")
                    return
                if count > len(living):
                    self.add_message(f"У вас только {len(living)} здоровых. Отправляем всех.")
                    count = len(living)
                if len(args) > 1:
                    if args[1] == 'новый':
                        is_new = True
                        region = 'новый'
                    else:
                        region = args[1]
            else:
                self.add_message("Неверный формат. Используйте 'отправить' или 'отправить новый'.")
                return
        else:
            # без аргументов: все на первую территорию
            pass

        # Проверка региона
        if not is_new:
            try:
                region_idx = int(region)
            except:
                self.add_message("Регион должен быть числом или 'новый'.")
                return
            if region_idx < 1 or region_idx > s.lands:
                self.add_message(f"Доступны регионы от 1 до {s.lands} или 'новый'.")
                return

        # Расчёт экипировки
        extra_equip_cost = 5 if is_new else 0
        need_equip = count * 3 + extra_equip_cost

        # Проверка хватает ли экипировки
        if s.equipment < need_equip:
            max_count = min(len(living), (s.equipment - extra_equip_cost) // 3)
            if max_count <= 0:
                self.add_message(f"❌ Недостаточно экипировки даже для одного человека. Нужно {3 + extra_equip_cost}, есть {s.equipment}.")
                return
            self.add_message(f"⚠️ Недостаточно экипировки для {count} человек. Нужно {need_equip}, есть {s.equipment}.")
            self.add_message(f"Вы можете отправить максимум {max_count} человек. Введите команду заново с нужным количеством, например: отправить {max_count} {region}")
            return

        # Выполнение экспедиции
        s.equipment -= need_equip

        # Выбираем первых count здоровых
        chosen = living[:count]
        if is_new:
            # Если есть древние карты, бонус к открытию
            open_bonus = 1 + s.map_bonus
            for _ in range(open_bonus):
                if s.lands < 20:  # ограничим
                    s.lands += 1
            self.add_message(f"🗺️ Открыта новая земля! (бонус от карт: +{open_bonus})")
            if s.has_ancient_maps:
                s.map_bonus = 0  # карты сработали один раз?

        # Расчёт добычи
        total_hunting = sum(t.hunting for t in chosen)
        synergy = self.synergy_multiplier(count)
        base_fur = total_hunting * 2 * synergy
        land_bonus = 1 + 0.1 * s.lands
        penalty = 1 - s.penalty_next_season / 100.0
        if penalty < 0: penalty = 0
        animal_bonus = 1 + 0.05 * s.total_animals()
        random_factor = random.uniform(0.8, 1.2)
        # Бонус от достижений
        perm_bonus = s.hunting_bonus_permanent
        # Бонус от шамана
        shaman_bonus = 1.0
        if self.hunting_boost:
            shaman_bonus = self.hunting_boost_multiplier
            self.hunting_boost = False
            self.hunting_boost_multiplier = 1.0
        fur_gained = int(base_fur * land_bonus * animal_bonus * penalty * random_factor * perm_bonus * shaman_bonus)
        if fur_gained < 0: fur_gained = 0

        # Проверка на учёного (составление карт)
        scientist_present = any(t.is_scientist for t in chosen)
        if is_new and scientist_present:
            s.maps_created += 1
            self.add_message("🧭 Учёный составил карту новой земли!")
            if s.maps_created % 3 == 0:
                s.charters += 1
                s.total_charters_earned += 1
                self.add_message("📜 Академия в Москве получила 3 карты! Царь жалует грамоту!")

        # Встреча с разбойниками
        bandit_chance = 0.2 * s.bandit_modifier
        if s.palisade:
            bandit_chance *= 0.5
        if random.random() < bandit_chance:
            self.add_message("\n🏴 ВНИМАНИЕ! На ваш отряд напали разбойники!")
            self.add_message("Что будешь делать?")
            self.add_message("  1 - Вступить в бой")
            self.add_message("  2 - Откупиться")
            self._bandit_count = count
            self._bandit_living = chosen
            self._bandit_fur_gained = fur_gained
            self.set_input_callback(self.process_bandit_choice, "Твой выбор (1 или 2): ")
            return
        else:
            self.add_message("✅ Поход прошёл без нападений.")

        s.fur += fur_gained
        self.add_message(f"🦊 Добыто {fur_gained} пушнины.")
        s.penalty_next_season = 0

        # Случайные события после экспедиции
        self.event_manager.random_event_after_expedition(chosen)

    # -------------------- ОБРАБОТКА ВЫБОРА ПРИ РАЗБОЙНИКАХ (без изменений) --------------------
    def process_bandit_choice(self, choice):
        # ... (оставляем как было)
        pass

    # -------------------- НОВЫЕ КОМАНДЫ --------------------
    def cmd_found_city(self, args):
        s = self.settlement
        required = 5 + len(s.cities) * 5
        if s.charters < required:
            self.add_message(f"❌ Для основания следующего города нужно {required} грамот, а у тебя только {s.charters}.")
            return
        if not args:
            self.add_message("Укажите название города: основать город <название>")
            return
        city_name = " ".join(args).strip()
        if not city_name:
            city_name = "Безымянный"
        s.charters -= required
        city = City(city_name)
        s.cities.append(city)
        s.city_names.append(city_name)  # для совместимости
        self.add_message(f"🏙️ Город {city_name} основан! Всего городов: {len(s.cities)}. Потрачено {required} грамот.")
        # Проверка на наличие железной руды или серебра в этом месте (генерируем случайно)
        if random.random() < 0.15:  # 15% шанс найти руду
            s.iron_deposits.append(city_name)
            city.has_iron_mine = True
            self.add_message("⛏️ В окрестностях найдена железная руда! Можно построить кузницу.")
        if random.random() < 0.08:  # 8% шанс найти серебро
            s.silver_deposits.append(city_name)
            city.has_silver_mine = True
            self.add_message("🥈 Обнаружено месторождение серебра! Это принесёт дополнительный доход.")
            # Царская милость за серебро
            s.charters += 1
            self.add_message("👑 Царь жалует грамоту за найденное серебро!")

    def cmd_build_blacksmith(self, args):
        s = self.settlement
        if not s.cities:
            self.add_message("Нет городов для постройки кузницы.")
            return
        # Ищем город с железной рудой и без кузницы
        target = None
        for city in s.cities:
            if city.has_iron_mine and not city.has_blacksmith:
                target = city
                break
        if not target:
            self.add_message("Нет подходящего города с железной рудой и без кузницы.")
            return
        if s.money < 200:
            self.add_message("Недостаточно денег. Нужно 200 руб.")
            return
        s.money -= 200
        target.has_blacksmith = True
        self.add_message(f"⚒️ В городе {target.name} построена кузница! Теперь экипировка стоит на 50% дешевле, и её можно продавать.")

    def cmd_sell_equipment(self, args):
        # Продажа экипировки (только если есть кузница в любом городе)
        s = self.settlement
        has_blacksmith = any(c.has_blacksmith for c in s.cities)
        if not has_blacksmith:
            self.add_message("Нет кузницы для продажи экипировки.")
            return
        if not args:
            self.add_message("Укажите количество экипировки для продажи.")
            return
        try:
            amount = int(args[0])
        except:
            self.add_message("Неверное число.")
            return
        if amount <= 0:
            self.add_message("Количество должно быть положительным.")
            return
        if amount > s.equipment:
            self.add_message(f"У вас только {s.equipment} экипировки.")
            return
        price_per_unit = 3  # цена продажи
        s.equipment -= amount
        s.money += amount * price_per_unit
        self.add_message(f"✅ Продано {amount} экипировки за {amount * price_per_unit} рублей.")

    def cmd_show_cities(self, args):
        s = self.settlement
        if not s.cities:
            self.add_message("Пока нет городов.")
            return
        for city in s.cities:
            lines = []
            lines.append(f"🏙️ {city.name} (река {city.river})")
            lines.append(f"   Население: {city.population}")
            amenities = []
            if city.has_church: amenities.append("храм")
            if city.has_hospital: amenities.append("лечебница")
            if city.has_blacksmith: amenities.append("кузница")
            if city.has_iron_mine: amenities.append("железная руда")
            if city.has_silver_mine: amenities.append("серебряная копь")
            if city.is_frontier: amenities.append("пограничная застава (чайная торговля)")
            if amenities:
                lines.append("   Постройки: " + ", ".join(amenities))
            else:
                lines.append("   Построек нет.")
            self.add_message("\n".join(lines))

    def cmd_show_leaderboard(self, args):
        # Локальная таблица лидеров (сохраняется в сессии)
        leaderboard = session.get('leaderboard', [])
        if not leaderboard:
            self.add_message("Таблица лидеров пуста. Стань первым!")
            return
        self.add_message("🏆 Таблица лидеров:")
        for i, entry in enumerate(leaderboard[:10], 1):
            self.add_message(f"{i}. {entry['name']} — грамот: {entry['charters']}, городов: {entry['cities']}")

    # -------------------- ОБРАБОТКА СОБЫТИЙ (расширение EventManager) --------------------
    # Некоторые методы уже есть, добавим новые события

# ============================ МЕНЕДЖЕР СОБЫТИЙ (расширенный) ============================
class EventManager:
    def __init__(self, game):
        self.game = game

    def random_event(self):
        """Стандартные случайные события (вызываются каждый сезон)"""
        if random.random() > 0.3:
            return
        s = self.game.settlement
        events = [
            self.event_find_fur,
            self.event_find_equipment,
            self.event_merchant_cheat,
            self.event_blizzard,
            self.event_animal_rampage,
            self.event_ancient_maps,
            self.event_iron_deposit,
            self.event_silver_deposit,
            self.event_tribe_shaman,
            self.event_tribe_marriage,
            self.event_china_border,  # шанс 4% внутри метода
        ]
        choice = random.choice(events)
        choice()

    def random_event_after_expedition(self, participants):
        """События, которые могут произойти после экспедиции (переломы)"""
        if random.random() < 0.08:  # 8% шанс травмы
            self.event_injury(participants)

    # -------------------- СУЩЕСТВУЮЩИЕ СОБЫТИЯ (оставляем) --------------------
    def event_find_fur(self):
        bonus = random.randint(10, 40)
        self.game.settlement.fur += bonus
        self.game.add_message(f"🎉 Случайная находка: обнаружено богатое соболиное гнездо! +{bonus} пушнины.")

    def event_find_equipment(self):
        bonus = random.randint(5, 20)
        self.game.settlement.equipment += bonus
        self.game.add_message(f"🎉 Найдена старая кладовая! +{bonus} экипировки.")

    def event_merchant_cheat(self):
        if self.game.settlement.money > 20:
            loss = random.randint(10, 50)
            self.game.settlement.money -= loss
            self.game.add_message(f"😤 Купец обвесил вас! Потеряно {loss} рублей.")
        else:
            self.game.add_message("Купец попытался обмануть, но у вас слишком мало денег – он ушёл ни с чем.")

    def event_blizzard(self):
        if self.game.settlement.season == 3:
            loss = random.randint(5, 15)
            self.game.settlement.equipment = max(0, self.game.settlement.equipment - loss)
            self.game.add_message(f"❄️ Снежная буря! Потеряно {loss} экипировки.")

    def event_animal_rampage(self):
        s = self.game.settlement
        if s.total_animals() > 0:
            loss = random.randint(1, min(3, s.total_animals()))
            for _ in range(loss):
                if s.dogs > 0:
                    s.dogs -= 1
                elif s.horses > 0:
                    s.horses -= 1
            self.game.add_message(f"🐾 Животные взбесились! Потеряно {loss} голов скота.")

    # -------------------- НОВЫЕ СОБЫТИЯ --------------------
    def event_ancient_maps(self):
        if not self.game.settlement.has_ancient_maps:
            self.game.settlement.has_ancient_maps = True
            self.game.settlement.map_bonus = 1
            self.game.add_message("🗺️ Вы нашли тайник с древними картами! Теперь открытие новых земель облегчено (+1 земля за экспедицию).")

    def event_iron_deposit(self):
        s = self.game.settlement
        if s.cities:
            city = random.choice(s.cities)
            if not city.has_iron_mine:
                city.has_iron_mine = True
                s.iron_deposits.append(city.name)
                self.game.add_message(f"⛏️ В окрестностях города {city.name} найдена железная руда! Можно построить кузницу.")

    def event_silver_deposit(self):
        s = self.game.settlement
        if s.cities:
            city = random.choice(s.cities)
            if not city.has_silver_mine:
                city.has_silver_mine = True
                s.silver_deposits.append(city.name)
                self.game.add_message(f"🥈 В окрестностях города {city.name} найдено месторождение серебра! Царь жалует грамоту!")
                s.charters += 1
                s.total_charters_earned += 1

    def event_tribe_shaman(self):
        s = self.game.settlement
        self.game.add_message("👣 Вы встретили местное племя. Шаман предлагает провести обряд охотничьей удачи.")
        self.game.add_message("Что будешь делать?")
        self.game.add_message("  1 - Отказаться")
        self.game.add_message("  2 - Попытаться обратить шамана в православие")
        self.game.set_input_callback(self.process_shaman_choice, "Твой выбор (1 или 2): ")

    def process_shaman_choice(self, choice):
        if choice == "1":
            self.game.add_message("Вы вежливо отказались. Шаман не обиделся.")
            return
        elif choice == "2":
            if random.random() < 0.5:
                # Успех
                self.game.add_message("🙏 Шаман принял православие! В благодарность он дарит вам экипировку и указывает места, богатые пушниной.")
                bonus_equip = random.randint(10, 30)
                self.game.settlement.equipment += bonus_equip
                self.game.add_message(f"Получено {bonus_equip} экипировки.")
                # Бонус к следующей охоте
                self.game.hunting_boost = True
                self.game.hunting_boost_multiplier = random.uniform(1.5, 2.0)
                self.game.add_message("Следующая экспедиция принесёт значительно больше пушнины!")
            else:
                self.game.add_message("Шаман не поддался на уговоры, но предложил вам обменяться дарами.")
                # даёт немного пушнины
                gift = random.randint(5, 15)
                self.game.settlement.fur += gift
                self.game.add_message(f"Вы получили {gift} пушнины в качестве дара.")
        else:
            self.game.add_message("Неверный ввод. Попробуй ещё раз.")
            self.event_tribe_shaman()  # повтор

    def event_tribe_marriage(self):
        s = self.game.settlement
        living = s.living_travelers()
        if not living:
            return
        if len(living) < 2:
            return
        groom = random.choice(living)
        # Исключаем Ермака? Пусть любой может жениться
        s.travelers.remove(groom)  # удаляем из списка
        self.game.add_message(f"💒 {groom.name} женился на местной девушке и решил остаться в племени. Он покидает отряд.")
        # возможно, добавить приданое?
        gift = random.randint(10, 30)
        s.money += gift
        self.game.add_message(f"Племя дарит вам {gift} рублей в качестве приданого.")

    def event_injury(self, participants):
        """Травма после экспедиции"""
        s = self.game.settlement
        if not participants:
            return
        victim = random.choice(participants)
        # Проверяем, есть ли врач среди участников (кроме самого пострадавшего)
        doctor = None
        for t in participants:
            if t.is_doctor and t != victim and t.alive and t.injured_until_season == -1:
                doctor = t
                break
        if doctor:
            caretaker = doctor
        else:
            # берём любого другого здорового (кроме victim)
            others = [t for t in s.living_travelers() if t != victim]
            if not others:
                # некому ухаживать, травма не происходит
                return
            caretaker = random.choice(others)

        # Отправляем их в список травмированных
        victim.injured_until_season = 2  # на два сезона
        caretaker.injured_until_season = 2
        s.injured_travelers.append((victim.name, 2, caretaker.name))
        self.game.add_message(f"🦴 {victim.name} сломал ногу во время похода. {caretaker.name} остаётся с ним на два сезона.")

    def event_china_border(self):
        """Шанс 4% (проверяем внутри) - после освоения 5 земель"""
        s = self.game.settlement
        if s.lands >= 5 and not self.game.china_discovered and random.random() < 0.04:
            self.game.china_discovered = True
            # Основать поселение и заставу
            city = City("Пограничная застава")
            city.is_frontier = True
            city.trade_bonus = 10  # доход от чая каждый сезон
            s.cities.append(city)
            s.city_names.append("Пограничная застава")
            self.game.add_message("🇨🇳 Ваш отряд достиг границы с Китаем! Основана пограничная застава. Теперь купцы могут торговать чаем, принося дополнительный доход.")
            # Добавляем постоянный доход
            # В after_action будем добавлять деньги от чая

    # В after_action добавим доход от чая:
    # for city in s.cities:
    #     if city.is_frontier:
    #         s.money += city.trade_bonus

# ============================ FLASK ПРИЛОЖЕНИЕ ============================
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST' and 'start_game' in request.form:
        name = request.form.get('player_name', '')
        email = request.form.get('player_email', '')
        session['player_name'] = name
        session['player_email'] = email
        game = Game()
        session['game_state'] = pickle.dumps(game)
        # Инициализируем таблицу лидеров
        if 'leaderboard' not in session:
            session['leaderboard'] = []
        return redirect(url_for('index'))

    if 'game_state' in session:
        game = pickle.loads(session['game_state'])
        if request.method == 'POST' and 'command' in request.form:
            command = request.form.get('command', '').strip().lower()
            if command:
                game.process_command(command)
                session['game_state'] = pickle.dumps(game)
                # Добавляем доход от чая
                s = game.settlement
                for city in s.cities:
                    if city.is_frontier:
                        s.money += city.trade_bonus

        status = game.get_status_text()
        messages = game.messages[-50:]
        image_index = game.current_image_index
        cities = game.settlement.cities
        achievements = game.achievements.completed
        noble_title = game.settlement.noble_title
        leaderboard = session.get('leaderboard', [])

        return render_template('index.html',
                               status=status,
                               messages=messages,
                               image_index=image_index,
                               cities=cities,
                               achievements=achievements,
                               noble_title=noble_title,
                               leaderboard=leaderboard)

    return render_template('start.html')

@app.route('/reset')
def reset():
    session.pop('game_state', None)
    return redirect(url_for('index'))

# Добавляем эндпоинт для добавления в таблицу лидеров
@app.route('/add_leaderboard', methods=['POST'])
def add_leaderboard():
    data = request.get_json()
    name = data.get('name', '')
    charters = data.get('charters', 0)
    cities = data.get('cities', 0)
    leaderboard = session.get('leaderboard', [])
    leaderboard.append({'name': name, 'charters': charters, 'cities': cities})
    # Сортируем по грамотам
    leaderboard.sort(key=lambda x: x['charters'], reverse=True)
    # Оставляем топ-10
    session['leaderboard'] = leaderboard[:10]
    return {'status': 'ok'}

if __name__ == '__main__':
    app.run(debug=True)
