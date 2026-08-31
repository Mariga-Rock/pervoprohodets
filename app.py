import random
import pickle
import json
from flask import Flask, request, render_template, session, redirect, url_for

# =================================================================
# КЛАССЫ
# =================================================================

class Traveler:
    def __init__(self, name):
        self.name = name
        self.hunting = random.randint(3, 7)
        self.endurance = random.randint(3, 7)
        self.alive = True
        self.scurvy = False
        self.is_doctor = random.random() < 0.1
        self.is_scientist = random.random() < 0.1
        self.injured_until_season = -1
        self.injured_with = None

    def ensure_attributes(self):
        if not hasattr(self, 'is_doctor'):
            self.is_doctor = random.random() < 0.1
        if not hasattr(self, 'is_scientist'):
            self.is_scientist = random.random() < 0.1
        if not hasattr(self, 'injured_until_season'):
            self.injured_until_season = -1
        if not hasattr(self, 'injured_with'):
            self.injured_with = None


class City:
    def __init__(self, name, river=None):
        self.name = name
        self.river = river or random.choice(["Обь", "Енисей", "Лена", "Иртыш", "Амур"])
        self.population = random.randint(50, 200)
        self.has_church = False
        self.has_hospital = False
        self.has_blacksmith = False
        self.has_iron_mine = False
        self.has_silver_mine = False
        self.is_frontier = False
        self.trade_bonus = 0


class Achievement:
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
        if not self.is_completed("first_city") and len(s.cities) >= 1:
            self.complete("first_city", game, "🏙️ Ты основал первый город! Отныне разбойники будут реже нападать.")
            s.bandit_modifier = 0.5
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
        self.city_names = []
        self.last_offer_level = 0
        self.patron_of_science = False
        self.benefactor = False
        # Новые поля
        self.cities = []
        self.iron_deposits = []
        self.silver_deposits = []
        self.has_ancient_maps = False
        self.map_bonus = 0
        self.maps_created = 0
        self.artifacts_found = 0
        self.hunting_bonus_permanent = 1.0
        self.morale_bonus = 1.0
        self.bandit_modifier = 1.0
        self.court_access = False
        self.noble_title = None
        self.injured_travelers = []
        self.tutorial_step = 0
        self.difficulty_modifier = 1.0
        self.leaderboard = []

    def total_animals(self):
        return self.dogs + self.horses

    def living_travelers(self):
        result = []
        for t in self.travelers:
            if t.alive and t.injured_until_season == -1:
                result.append(t)
        return result

    def all_alive(self):
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

    def ensure_attributes(self):
        if not hasattr(self, 'cities'):
            self.cities = []
        if not hasattr(self, 'iron_deposits'):
            self.iron_deposits = []
        if not hasattr(self, 'silver_deposits'):
            self.silver_deposits = []
        if not hasattr(self, 'has_ancient_maps'):
            self.has_ancient_maps = False
        if not hasattr(self, 'map_bonus'):
            self.map_bonus = 0
        if not hasattr(self, 'maps_created'):
            self.maps_created = 0
        if not hasattr(self, 'artifacts_found'):
            self.artifacts_found = 0
        if not hasattr(self, 'hunting_bonus_permanent'):
            self.hunting_bonus_permanent = 1.0
        if not hasattr(self, 'morale_bonus'):
            self.morale_bonus = 1.0
        if not hasattr(self, 'bandit_modifier'):
            self.bandit_modifier = 1.0
        if not hasattr(self, 'court_access'):
            self.court_access = False
        if not hasattr(self, 'noble_title'):
            self.noble_title = None
        if not hasattr(self, 'injured_travelers'):
            self.injured_travelers = []
        if not hasattr(self, 'tutorial_step'):
            self.tutorial_step = 0
        if not hasattr(self, 'difficulty_modifier'):
            self.difficulty_modifier = 1.0
        for t in self.travelers:
            t.ensure_attributes()


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
        self.total_cases_scurvy = 0
        self.hunting_boost = False
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

    def ensure_attributes(self):
        if not hasattr(self, 'total_cases_scurvy'):
            self.total_cases_scurvy = 0
        if not hasattr(self, 'hunting_boost'):
            self.hunting_boost = False
        if not hasattr(self, 'hunting_boost_multiplier'):
            self.hunting_boost_multiplier = 1.0
        if not hasattr(self, 'tutorial_messages_shown'):
            self.tutorial_messages_shown = set()
        if not hasattr(self, 'china_discovered'):
            self.china_discovered = False
        if not hasattr(self, 'achievements'):
            self.achievements = Achievement()
        if not hasattr(self, 'current_image_index'):
            self.current_image_index = random.randint(1, 3)
        self.settlement.ensure_attributes()

    # ================ ОСТАЛЬНЫЕ МЕТОДЫ ================

    def adjust_difficulty(self):
        s = self.settlement
        if len([t for t in s.travelers if not t.alive]) > 2:
            s.difficulty_modifier = max(0.8, s.difficulty_modifier - 0.05)
        if s.money < -50:
            s.difficulty_modifier = max(0.7, s.difficulty_modifier - 0.1)
        if s.charters > 10 and s.lands > 5:
            s.difficulty_modifier = min(1.3, s.difficulty_modifier + 0.05)
        s.difficulty_modifier = max(0.6, min(1.4, s.difficulty_modifier))

    def tutorial_advice(self):
        s = self.settlement
        step = s.tutorial_step
        if step == 0 and s.season == 1 and len(s.living_travelers()) == 2:
            self.add_message("💡 Подсказка: Лето — лучшее время для экспедиций. Попробуй отправиться за пушниной! (команда 'Отправиться за пушниной' или 'отправить')")
            s.tutorial_step = 1
        elif step == 1 and s.fur > 0 and s.season == 2:
            self.add_message("💡 Подсказка: Осенью можно продать пушнину. Введи 'Продать пушнину <количество>'.")
            s.tutorial_step = 2
        elif step == 2 and s.equipment < 5 and s.money > 20:
            self.add_message("💡 Подсказка: У тебя мало экипировки. Купи её командой 'Купить экипировку <количество>' (5 руб/ед).")
            s.tutorial_step = 3
        elif step == 3 and s.season == 3 and s.cabbage == 0:
            self.add_message("💡 Подсказка: Зима близко! Запасись квашеной капустой осенью, чтобы избежать голода.")
            s.tutorial_step = 4
        if len(s.cities) == 1 and not self.has_shown_tutorial("city"):
            self.add_message("💡 Подсказка: Ты основал город! В нём можно построить храм и лечебницу, если есть врач.")
            self.mark_tutorial_shown("city")
        if s.charters >= 5 and not self.has_shown_tutorial("charter"):
            self.add_message("💡 Подсказка: У тебя 5 грамот! Теперь можно основать город (команда 'Основать город <название>').")
            self.mark_tutorial_shown("charter")

    def has_shown_tutorial(self, key):
        return key in self.tutorial_messages_shown

    def mark_tutorial_shown(self, key):
        self.tutorial_messages_shown.add(key)

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

        # Замена новых команд на синонимы для удобства
        if cmd.startswith('отправиться за пушниной'):
            cmd = 'отправить' + cmd[len('отправиться за пушниной'):]
        if cmd.startswith('спонсировать научные исследования'):
            cmd = 'пожертвовать науке' + cmd[len('спонсировать научные исследования'):]
        if cmd.startswith('послать деньги семье'):
            cmd = 'отправить семье' + cmd[len('послать деньги семье'):]
        if cmd.startswith('показать статус'):
            cmd = 'статус' + cmd[len('показать статус'):]
        if cmd.startswith('переждать до следующей весны'):
            cmd = 'пропустить год' + cmd[len('переждать до следующей весны'):]

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

        for city in s.cities:
            if city.is_frontier:
                s.money += city.trade_bonus

        self.achievements.check_and_reward(self)
        self.tutorial_advice()
        self.adjust_difficulty()
        self.process_injuries()
        for city in s.cities:
            city.population += random.randint(0, 3)
        if s.charters >= 5:
            current_level = s.charters // 5
            if current_level > s.last_offer_level:
                self.offer_charter_choice()
        if s.total_fur_sent_to_tsar >= 1000 and s.noble_title is None:
            s.noble_title = 'дворянин'
            self.add_message("👑 Царь жалует тебе дворянское звание за твои заслуги! Ты теперь дворянин.")
        if s.total_fur_sent_to_tsar >= 10000 and s.noble_title != 'вельможа':
            s.noble_title = 'вельможа'
            self.add_message("👑 Великая честь! Ты стал вельможей! Но помни: с большим богатством приходит и большая ответственность.")

    def get_status_text(self):
        s = self.settlement
        season_names = ["🌸 Весна", "☀️ Лето", "🍂 Осень", "❄️ Зима"]
        lines = []
        lines.append(f"Год {s.year}, сезон: {season_names[s.season]}")
        lines.append(f"Путешественников: {len(s.living_travelers())} (всего {len(s.all_alive())})")
        if s.count_scurvy() > 0:
            lines.append(f"   (Цинга: {s.count_scurvy()} больных)")
        lines.append(f"Пушнина: {s.fur} | Экипировка: {s.equipment} | Деньги: {s.money} руб.")
        lines.append(f"Собаки/лошади: {s.dogs}/{s.horses} (всего {s.total_animals()})")
        lines.append(f"Открытые земли: {s.lands} | Царские грамоты: {s.charters}")
        if s.cities:
            lines.append(f"Городов: {len(s.cities)}")
        if s.has_ancient_maps:
            lines.append("🗺️ У тебя есть древние карты (+1 к открытию новых земель)")
        if s.maps_created > 0:
            lines.append(f"🗺️ Составлено карт: {s.maps_created} (каждые 3 дают грамоту)")
        if s.noble_title:
            lines.append(f"👑 Титул: {s.noble_title}")
        if s.court_access:
            lines.append("🏛️ Доступ к царскому двору")
        if s.patron_of_science:
            lines.append("🔬 Меценат")
        if s.benefactor:
            lines.append("❤️ Благотворитель")
        if s.penalty_next_season > 0:
            lines.append(f"⚠️ Штраф к добыче: -{s.penalty_next_season}%")
        if s.season == 2:
            price_mod = self.get_fur_price_modifier()
            lines.append(f"💰 Цена пушнины у купцов: {self.merchant_price * price_mod:.1f} руб./ед. (можно продавать)")
        return "\n".join(lines)

    def heal_scurvy_with_cabbage(self):
        s = self.settlement
        sick = [t for t in s.living_travelers() if t.scurvy]
        if not sick:
            return
        healed = 0
        for t in sick:
            if s.cabbage > 0:
                t.scurvy = False
                s.cabbage -= 1
                healed += 1
                self.add_message(f"🥬 {t.name} вылечен от цинги квашеной капустой.")
                self.total_cases_scurvy += 1
            else:
                break
        if healed > 0 and s.has_scurvy():
            self.add_message("⚠️ Не хватило капусты, некоторые путешественники всё ещё больны.")
        elif healed > 0:
            self.add_message("💚 Все больные цингой вылечены!")

    def check_debt(self):
        s = self.settlement
        if s.money <= -20:
            self.add_message("\n⚠️ Твои долги достигли критической отметки (-20 рублей)! Нужно срочно найти деньги.")
            options = []
            if s.dogs > 0:
                options.append("1 - Продать собаку (30 руб)")
            if s.horses > 0:
                options.append("2 - Продать лошадь (50 руб)")
            if s.church:
                options.append("3 - Обратиться в храм за помощью (случайно)")
            if not options:
                self.add_message("💀 У тебя нет никаких активов, чтобы расплатиться. Игра окончена.")
                self.running = False
                return
            self.add_message("Выбери действие:")
            for opt in options:
                self.add_message("  " + opt)
            self.set_input_callback(self.process_debt_choice, "Твой выбор: ")

    def process_debt_choice(self, choice):
        s = self.settlement
        if choice == "1" and s.dogs > 0:
            s.dogs -= 1
            s.money += 30
            self.add_message("🐕 Ты продал собаку за 30 рублей. Долг погашен.")
        elif choice == "2" and s.horses > 0:
            s.horses -= 1
            s.money += 50
            self.add_message("🐎 Ты продал лошадь за 50 рублей. Долг погашен.")
        elif choice == "3" and s.church:
            if random.random() < 0.5:
                donation = random.randint(30, 60)
                s.money += donation
                self.add_message(f"🙏 Храм помог тебе! Ты получил {donation} рублей.")
            else:
                self.add_message("🙏 Храм не смог помочь, но ты можешь попробовать ещё раз позже.")
        else:
            self.add_message("❌ Неверный выбор. Попробуй ещё раз.")
            self.check_debt()

    def process_injuries(self):
        s = self.settlement
        new_injured = []
        for entry in s.injured_travelers:
            name, seasons_left, caretaker = entry
            seasons_left -= 1
            if seasons_left <= 0:
                for t in s.travelers:
                    if t.name == name and t.alive:
                        t.injured_until_season = -1
                        self.add_message(f"💚 {name} полностью оправился от травмы и вернулся в отряд!")
                        if caretaker:
                            for c in s.travelers:
                                if c.name == caretaker and c.alive:
                                    c.injured_until_season = -1
                                    self.add_message(f"💚 {caretaker} вернулся в отряд после ухода за больным.")
                        break
            else:
                new_injured.append((name, seasons_left, caretaker))
        s.injured_travelers = new_injured

    def offer_charter_choice(self):
        s = self.settlement
        self._charter_level = s.charters // 5
        self.add_message(f"\n🦅 Ты достиг {s.charters} царских грамот! Теперь у тебя есть выбор:")
        self.add_message("  1 - Основать город (потратить 5 грамот) — город будет назван твоим именем.")
        self.add_message("  2 - Получить двух новых путешественников в отряд (грамоты останутся).")
        self.set_input_callback(self.process_charter_choice, "Твой выбор (1 или 2): ")

    def process_charter_choice(self, choice):
        s = self.settlement
        level = self._charter_level
        if choice == "1":
            if s.charters >= 5:
                self.cmd_found_city(["неважно"])
            else:
                self.add_message("❌ Что-то пошло не так: грамот недостаточно.")
            s.last_offer_level = level
        elif choice == "2":
            names = ["Семён", "Демид", "Артемий", "Прокопий", "Гаврила"]
            for _ in range(2):
                name = random.choice(names) + " (новый)"
                new_t = Traveler(name)
                s.travelers.append(new_t)
            self.add_message(f"👥 Два новых путешественника присоединились к твоему отряду! Теперь у тебя {len(s.living_travelers())} человек.")
            s.last_offer_level = level
        else:
            self.add_message("❌ Неверный ввод. Попробуй ещё раз.")
            self.offer_charter_choice()

    def synergy_multiplier(self, count):
        if count <= 0: return 0
        if count == 1: return 1.0
        if count == 2: return 2.5
        if count == 3: return 7.5
        return 7.5 * (1.3 ** (count - 3))

    def advance_season(self):
        s = self.settlement
        s.season = (s.season + 1) % 4
        if s.season == 1:
            healed_count = 0
            for t in s.living_travelers():
                if t.scurvy:
                    t.scurvy = False
                    healed_count += 1
            if healed_count > 0:
                self.add_message(f"☀️ С приходом лета все {healed_count} путешественников излечились от цинги!")
            else:
                self.add_message("☀️ Наступило лето. Все здоровы.")
        if s.season == 0:
            s.year += 1
            self.merchant_price = random.randint(2, 10)
            self.add_message(f"🎉 Поздравляем! Ты занимаешься освоением Сибири в течение уже {s.year} лет. За это время тебе на самом высочайшем уровне пожаловали {s.total_charters_earned} грамот.")
        if s.season == 3:
            self.winter_consumption()
        self.check_drunkard()
        self.event_manager.random_event()

    def winter_consumption(self):
        s = self.settlement
        num_travelers = len(s.living_travelers())
        cabbage_before = s.cabbage
        if s.cabbage > 0:
            cabbage_spent = min(s.cabbage, num_travelers)
            s.cabbage -= cabbage_spent
            if cabbage_spent > 0:
                self.add_message(f"❄️ Зимой потрачено {cabbage_spent} квашеной капусты на пропитание (осталось: {s.cabbage})")
        else:
            cabbage_spent = 0
            self.add_message("🥬 Капусты нет – зимний расход пропущен.")
        had_enough_cabbage = cabbage_before >= num_travelers
        need_equip = num_travelers * 2
        need_fur = num_travelers * 1
        need_equip += s.total_animals() * 2
        need_fur += s.total_animals() * 1
        deficit_equip = max(0, need_equip - s.equipment)
        deficit_fur = max(0, need_fur - s.fur)
        if not had_enough_cabbage and (deficit_equip > 0 or deficit_fur > 0):
            deaths = (deficit_equip + deficit_fur) // 5
            if deaths > 0:
                living = s.living_travelers()
                for _ in range(min(deaths, len(living))):
                    victim = random.choice(living)
                    victim.alive = False
                    living.remove(victim)
                self.add_message(f"❄️ Зимний голод! Умерло {deaths} путешественников.")
            else:
                self.add_message("❄️ Зимой ресурсов не хватило, но голод не привёл к смертям.")
        elif had_enough_cabbage:
            if deficit_equip > 0 or deficit_fur > 0:
                self.add_message("🥬 Благодаря квашеной капусте зимний голод не унёс ни одной жизни!")
        else:
            self.add_message("❄️ Зима прошла благополучно, ресурсов хватило.")
        s.equipment = max(0, s.equipment - need_equip)
        s.fur = max(0, s.fur - need_fur)
        s.remove_dead()

    def check_drunkard(self):
        s = self.settlement
        threshold = 3000 if s.church else 2000
        if s.money > threshold:
            if s.charters > 0:
                s.charters -= 1
                s.money -= 500
                self.add_message(f"🍺 Пьянство и разгул! Царь отнял 1 грамоту. Осталось грамот: {s.charters}")
            else:
                s.penalty_next_season += 30
                self.add_message("🍺 Пьянство и лень! Путешественники будут добывать меньше пушнины в следующем сезоне.")
                s.money = threshold

    def get_fur_price_modifier(self):
        s = self.settlement
        return max(0.5, 1 - (s.fur / 5000))

    # ================ КОМАНДЫ ================

    def cmd_help(self, args):
        self.add_message(self.get_help_text())

    def get_help_text(self):
        return """
Список команд (вводите с большой буквы или строчными — неважно):

  Отправиться за пушниной [кол-во] [регион] – экспедиция (только летом). По умолчанию – все на первую территорию.
  Отправиться за пушниной новый           – исследовать новую территорию (все здоровые).
  Продать пушнину <кол-во>             – продать пушнину (только осенью). Цена зависит от запасов.
  Послать пушнину в царскую казну <кол-во> – 100 пушнины = 1 грамота.
  Купить экипировку <кол-во>           – купить экипировку (цена зависит от кузницы).
  Купить собаку [кол-во]               – купить собак (50 руб/шт).
  Купить лошадь [кол-во]               – купить лошадей (50 руб/шт).
  Купить квашеную капусту <кол-во>     – только осенью (10 руб/ед).
  Построить храм                       – построить храм в текущем городе (500 руб).
  Построить частокол                   – защита от разбойников (100 руб).
  Построить кузницу                    – если есть железная руда в городе (200 руб).
  Подкупить разбойников <сумма>        – снизить активность.
  Послать деньги семье <сумма>         – отправить деньги семье.
  Основать город <название>            – требуется 5+5*число_городов грамот.
  Спонсировать научные исследования <сумма> – стать меценатом (≥200 руб).
  Пожертвовать сирым <сумма>           – стать благотворителем (≥150 руб).
  Показать статус                      – показать состояние.
  Следующий сезон                      – перейти к следующему сезону.
  Переждать до следующей весны         – пропустить год (50 руб + 2 капусты).
  Города                               – показать информацию о городах.
  Лидеры                               – таблица лидеров.
  Помощь                               – показать эту справку.
  Выход                                – выйти.

Новые возможности:
  - Учёные составляют карты (каждые 3 карты = 1 грамота).
  - Врачи помогают при травмах, могут открыть лечебницу в городе.
  - Месторождения руды и серебра позволяют строить кузницы и получать доход.
  - Встречи с племенами дают выбор: обряд удачи или обращение в православие.
  - Достижения открывают постоянные бонусы.
  - При 1000 пушнины – дворянство, при 10000 – вельможа.
  - Граница с Китаем (шанс 4%) открывает чайную торговлю.
        """

    def cmd_status(self, args):
        self.display_status()

    def display_status(self):
        self.add_message(self.get_status_text())

    def cmd_skip(self, args):
        self.advance_season()
        if self.running:
            self.check_game_over()

    def cmd_skip_year(self, args):
        s = self.settlement
        if s.money < 50:
            self.add_message("❌ Недостаточно денег для пропуска года (нужно 50 руб.).")
            return
        s.money -= 50
        if s.cabbage > 0:
            spent_cabbage = min(2, s.cabbage)
            s.cabbage -= spent_cabbage
            self.add_message(f"🥬 Потрачено {spent_cabbage} квашеной капусты.")
        else:
            self.add_message("🥬 Капусты не было – пропускаем без неё.")
        for t in s.living_travelers():
            t.endurance = max(1, t.endurance - 1)
        s.penalty_next_season = 0
        s.year += 1
        s.season = 0
        self.merchant_price = random.randint(2, 10)
        self.add_message(f"⏩ Ты переждал до следующей весны! Теперь год {s.year}, сезон Весна.")
        self.add_message(f"🎉 Поздравляем! Ты занимаешься освоением Сибири в течение уже {s.year} лет. За это время тебе на самом высочайшем уровне пожаловали {s.total_charters_earned} грамот.")
        if self.running:
            self.check_game_over()

    def cmd_sell(self, args):
        if self.settlement.season != 2:
            self.add_message("❌ Продавать пушнину можно только осенью!")
            return
        if not args:
            self.add_message("Укажите количество пушнины для продажи.")
            return
        try:
            amount = int(args[0])
        except:
            self.add_message("Неверное число.")
            return
        s = self.settlement
        if amount <= 0:
            self.add_message("Количество должно быть положительным.")
            return
        if amount > s.fur:
            self.add_message(f"У вас только {s.fur} пушнины.")
            return
        s.fur -= amount
        price_mod = self.get_fur_price_modifier()
        revenue = int(amount * self.merchant_price * price_mod)
        bonus = 1 + 0.1 * s.charters
        revenue = int(revenue * bonus)
        s.money += revenue
        self.add_message(f"✅ Продано {amount} пушнины за {revenue} рублей.")

    def cmd_give_to_tsar(self, args):
        if not args:
            self.add_message("Укажите количество пушнины для отправки в царскую казну.")
            return
        try:
            amount = int(args[0])
        except:
            self.add_message("Неверное число.")
            return
        s = self.settlement
        if amount <= 0:
            self.add_message("Количество должно быть положительным.")
            return
        if amount > s.fur:
            self.add_message(f"У вас только {s.fur} пушнины.")
            return
        earned = amount // 100
        if earned == 0:
            self.add_message("Нужно как минимум 100 пушнины для получения грамоты.")
            return
        s.fur -= amount
        s.charters += earned
        s.total_charters_earned += earned
        s.total_fur_sent_to_tsar += amount
        self.add_message(f"👑 Отправлено {amount} пушнины в царскую казну. Царь пожаловал тебе {earned} грамот! Всего грамот: {s.charters}.")

    def cmd_expedition(self, args):
        if self.settlement.season != 1:
            self.add_message("❌ Экспедиции возможны только летом!")
            return
        s = self.settlement
        living = s.living_travelers()
        if not living:
            self.add_message("Нет здоровых путешественников.")
            return

        count = len(living)
        region = '1'
        is_new = False

        if args:
            first = args[0]
            if first == 'новый':
                is_new = True
                region = 'новый'
                if len(args) > 1:
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
                self.add_message("Неверный формат. Используйте 'Отправиться за пушниной' или 'Отправиться за пушниной новый'.")
                return

        if not is_new:
            try:
                region_idx = int(region)
            except:
                self.add_message("Регион должен быть числом или 'новый'.")
                return
            if region_idx < 1 or region_idx > s.lands:
                self.add_message(f"Доступны регионы от 1 до {s.lands} или 'новый'.")
                return

        extra_equip_cost = 5 if is_new else 0
        need_equip = count * 3 + extra_equip_cost

        if s.equipment < need_equip:
            max_count = min(len(living), (s.equipment - extra_equip_cost) // 3)
            if max_count <= 0:
                self.add_message(f"❌ Недостаточно экипировки даже для одного человека. Нужно {3 + extra_equip_cost}, есть {s.equipment}.")
                return
            self.add_message(f"⚠️ Недостаточно экипировки для {count} человек. Нужно {need_equip}, есть {s.equipment}.")
            self.add_message(f"Вы можете отправить максимум {max_count} человек. Введите команду заново с нужным количеством, например: Отправиться за пушниной {max_count} {region}")
            return

        s.equipment -= need_equip
        chosen = living[:count]

        if is_new:
            open_bonus = 1 + s.map_bonus
            for _ in range(open_bonus):
                if s.lands < 20:
                    s.lands += 1
            self.add_message(f"🗺️ Открыта новая земля! (бонус от карт: +{open_bonus})")
            if s.has_ancient_maps:
                s.map_bonus = 0

        total_hunting = sum(t.hunting for t in chosen)
        synergy = self.synergy_multiplier(count)
        base_fur = total_hunting * 2 * synergy
        land_bonus = 1 + 0.1 * s.lands
        penalty = 1 - s.penalty_next_season / 100.0
        if penalty < 0: penalty = 0
        animal_bonus = 1 + 0.05 * s.total_animals()
        random_factor = random.uniform(0.8, 1.2)
        perm_bonus = s.hunting_bonus_permanent
        shaman_bonus = 1.0
        if self.hunting_boost:
            shaman_bonus = self.hunting_boost_multiplier
            self.hunting_boost = False
            self.hunting_boost_multiplier = 1.0
        fur_gained = int(base_fur * land_bonus * animal_bonus * penalty * random_factor * perm_bonus * shaman_bonus)
        if fur_gained < 0: fur_gained = 0

        scientist_present = any(t.is_scientist for t in chosen)
        if is_new and scientist_present:
            s.maps_created += 1
            self.add_message("🧭 Учёный составил карту новой земли!")
            if s.maps_created % 3 == 0:
                s.charters += 1
                s.total_charters_earned += 1
                self.add_message("📜 Академия в Москве получила 3 карты! Царь жалует грамоту!")

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
        self.event_manager.random_event_after_expedition(chosen)

    def process_bandit_choice(self, choice):
        s = self.settlement
        count = self._bandit_count
        living = self._bandit_living
        fur_gained = self._bandit_fur_gained
        fight = False
        if choice == "2":
            ransom = random.randint(30, 100)
            if s.money >= ransom:
                s.money -= ransom
                self.add_message(f"💰 Ты заплатил {ransom} рублей. Разбойники приняли плату и ушли.")
                fight = False
            else:
                self.add_message(f"😤 У тебя всего {s.money} рублей, а нужно {ransom}. Денег не хватает – придётся драться!")
                fight = True
        elif choice == "1":
            fight = True
        else:
            self.add_message("❌ Неверный ввод. Попробуй ещё раз.")
            self.add_message("Что будешь делать?")
            self.add_message("  1 - Вступить в бой")
            self.add_message("  2 - Откупиться")
            self.set_input_callback(self.process_bandit_choice, "Твой выбор (1 или 2): ")
            return
        if fight:
            self.add_message("⚔️ Ты вступаешь в бой с разбойниками!")
            killed_in_battle = 0
            stolen = 0
            for t in living[:count]:
                loss = random.randint(1, 2)
                t.endurance = max(1, t.endurance - loss)
            self.add_message("💪 Путешественники потеряли часть выносливости в бою.")
            if s.dogs > 0 or s.horses > 0:
                if random.random() < 0.3:
                    if s.horses > 0:
                        s.horses -= 1
                        self.add_message("🐎 Разбойники убили одну лошадь.")
                    elif s.dogs > 0:
                        s.dogs -= 1
                        self.add_message("🐕 Разбойники убили одну собаку.")
            if random.random() < 0.2:
                stolen = fur_gained // 3
                if stolen > 0:
                    fur_gained -= stolen
                    self.add_message(f"🏴 Разбойники украли {stolen} пушнины.")
            if random.random() < 0.1:
                victims = random.sample(living[:count], min(1, count))
                for v in victims:
                    v.alive = False
                killed_in_battle = len(victims)
                self.add_message(f"⚔️ Разбойники убили {killed_in_battle} путешественника(ов).")
                s.remove_dead()
            self.add_message("✅ Бой окончен. Отряд продолжает путь.")
            if killed_in_battle == 0 and stolen == 0:
                self.add_message("Разбойники ушли ни с чем.")
            elif killed_in_battle > 0:
                self.add_message(f"⚔️ В бою погибло {killed_in_battle} путешественников.")
        s.fur += fur_gained
        self.add_message(f"🦊 Добыто {fur_gained} пушнины.")
        s.penalty_next_season = 0

    def cmd_buy_equipment(self, args):
        if not args:
            self.add_message("Укажите количество экипировки для покупки.")
            return
        try:
            amount = int(args[0])
        except:
            self.add_message("Неверное число.")
            return
        s = self.settlement
        price_per_unit = 5
        if any(c.has_blacksmith for c in s.cities):
            price_per_unit = 2
        cost = amount * price_per_unit
        if cost > s.money:
            self.add_message(f"Недостаточно денег. Нужно {cost}, есть {s.money}.")
            return
        s.money -= cost
        s.equipment += amount
        self.add_message(f"✅ Куплено {amount} экипировки. Осталось денег: {s.money}.")

    def cmd_buy_dog(self, args):
        s = self.settlement
        if args and args[0].isdigit():
            count = int(args[0])
        else:
            count = 1
        if count <= 0:
            self.add_message("Количество должно быть положительным.")
            return
        total_cost = count * 50
        if s.money < total_cost:
            self.add_message(f"Недостаточно денег. Нужно {total_cost} руб., есть {s.money}.")
            return
        s.money -= total_cost
        s.dogs += count
        self.add_message(f"🐕 Куплено {count} собак. Всего собак: {s.dogs}")

    def cmd_buy_horse(self, args):
        s = self.settlement
        if args and args[0].isdigit():
            count = int(args[0])
        else:
            count = 1
        if count <= 0:
            self.add_message("Количество должно быть положительным.")
            return
        total_cost = count * 50
        if s.money < total_cost:
            self.add_message(f"Недостаточно денег. Нужно {total_cost} руб., есть {s.money}.")
            return
        s.money -= total_cost
        s.horses += count
        self.add_message(f"🐎 Куплено {count} лошадей. Всего лошадей: {s.horses}")

    def cmd_buy_cabbage(self, args):
        if self.settlement.season != 2:
            self.add_message("❌ Квашеную капусту можно покупать только осенью!")
            return
        if not args:
            self.add_message("Укажите количество капусты.")
            return
        try:
            amount = int(args[0])
        except:
            self.add_message("Неверное число.")
            return
        s = self.settlement
        if amount <= 0:
            self.add_message("Количество должно быть положительным.")
            return
        cost = amount * 10
        if cost > s.money:
            self.add_message(f"Недостаточно денег. Нужно {cost}, есть {s.money}.")
            return
        s.money -= cost
        sick = [t for t in s.living_travelers() if t.scurvy]
        healed = min(len(sick), amount)
        for i in range(healed):
            sick[i].scurvy = False
        remaining = amount - healed
        s.cabbage += remaining
        self.add_message(f"🥬 Куплено {amount} квашеной капусты. Из них {healed} использовано на лечение цинги, {remaining} добавлено в запас.")
        if healed > 0:
            self.add_message(f"💚 Вылечено {healed} путешественников от цинги.")
            self.total_cases_scurvy += healed
        if s.cabbage == 0:
            self.add_message("Вся капуста ушла на лечение, запаса не осталось.")
        else:
            self.add_message(f"Теперь в запасе {s.cabbage} капусты.")

    def cmd_build_church(self, args):
        s = self.settlement
        target = None
        for city in s.cities:
            if not city.has_church:
                target = city
                break
        if not target:
            self.add_message("Нет подходящего города для постройки храма.")
            return
        if s.money < 500:
            self.add_message("Недостаточно денег. Нужно 500 руб.")
            return
        s.money -= 500
        target.has_church = True
        self.add_message(f"🏛️ В городе {target.name} построен храм! Теперь порог пьянства повышен до 3000 рублей, и при долгах можно обратиться за помощью.")

    def cmd_build_palisade(self, args):
        s = self.settlement
        if s.palisade:
            self.add_message("Частокол уже построен.")
            return
        if s.money < 100:
            self.add_message("Недостаточно денег. Нужно 100 руб.")
            return
        s.money -= 100
        s.palisade = True
        self.add_message("🛡️ Частокол построен! Риск нападений разбойников снижен.")

    def cmd_bribe_bandits(self, args):
        if not args:
            self.add_message("Укажите сумму для подкупа.")
            return
        try:
            amount = int(args[0])
        except:
            self.add_message("Неверное число.")
            return
        s = self.settlement
        if amount > s.money:
            self.add_message("Недостаточно денег.")
            return
        s.money -= amount
        self.bandit_activity = max(0.05, self.bandit_activity - 0.1)
        self.add_message(f"🤝 Разбойники подкуплены на {amount} руб. Активность снижена.")

    def cmd_send_money_to_family(self, args):
        if not args:
            self.add_message("Укажите сумму для отправки семье.")
            return
        try:
            amount = int(args[0])
        except:
            self.add_message("Неверное число.")
            return
        s = self.settlement
        if amount <= 0:
            self.add_message("Сумма должна быть положительной.")
            return
        if amount > s.money:
            self.add_message(f"У вас только {s.money} рублей. Не хватает.")
            return
        s.money -= amount
        self.add_message(f"📨 Ты отправил {amount} рублей своей семье. Семья передаёт спасибо и очень гордится твоими успехами! ❤️")

    def cmd_found_city(self, args):
        s = self.settlement
        required = 5 + len(s.cities) * 5
        if s.charters < required:
            self.add_message(f"❌ Для основания следующего города нужно {required} грамот, а у тебя только {s.charters}.")
            return
        if not args:
            self.add_message("Укажите название города: Основать город <название>")
            return
        city_name = " ".join(args).strip()
        if not city_name:
            city_name = "Безымянный"
        s.charters -= required
        city = City(city_name)
        s.cities.append(city)
        s.city_names.append(city_name)
        self.add_message(f"🏙️ Город {city_name} основан! Всего городов: {len(s.cities)}. Потрачено {required} грамот.")
        if random.random() < 0.15:
            s.iron_deposits.append(city_name)
            city.has_iron_mine = True
            self.add_message("⛏️ В окрестностях найдена железная руда! Можно построить кузницу.")
        if random.random() < 0.08:
            s.silver_deposits.append(city_name)
            city.has_silver_mine = True
            self.add_message("🥈 Обнаружено месторождение серебра! Это принесёт дополнительный доход.")
            s.charters += 1
            self.add_message("👑 Царь жалует грамоту за найденное серебро!")

    def cmd_donate_science(self, args):
        if not args:
            self.add_message("Укажите сумму для спонсирования научных исследований.")
            return
        try:
            amount = int(args[0])
        except:
            self.add_message("Неверное число.")
            return
        s = self.settlement
        if amount <= 0:
            self.add_message("Сумма должна быть положительной.")
            return
        if amount > s.money:
            self.add_message(f"У вас только {s.money} рублей. Не хватает.")
            return
        if amount < 200:
            self.add_message("Минимальное пожертвование – 200 рублей.")
            return
        s.money -= amount
        if not s.patron_of_science:
            s.patron_of_science = True
            self.add_message("🔬 Ты стал меценатом! Наука в Сибири получит развитие. Спасибо за твой вклад!")
        else:
            self.add_message("🔬 Ты уже меценат. Дополнительное пожертвование принято с благодарностью.")
        self.add_message(f"Пожертвовано {amount} рублей на развитие науки.")

    def cmd_donate_charity(self, args):
        if not args:
            self.add_message("Укажите сумму для пожертвования на помощь сирым.")
            return
        try:
            amount = int(args[0])
        except:
            self.add_message("Неверное число.")
            return
        s = self.settlement
        if amount <= 0:
            self.add_message("Сумма должна быть положительной.")
            return
        if amount > s.money:
            self.add_message(f"У вас только {s.money} рублей. Не хватает.")
            return
        if amount < 150:
            self.add_message("Минимальное пожертвование – 150 рублей.")
            return
        s.money -= amount
        if not s.benefactor:
            s.benefactor = True
            self.add_message("❤️ Ты стал благотворителем! Твоя помощь сирым и убогим будет помнить вся Сибирь!")
        else:
            self.add_message("❤️ Ты уже благотворитель. Дополнительное пожертвование принято с благодарностью.")
        self.add_message(f"Пожертвовано {amount} рублей на помощь нуждающимся.")

    def cmd_build_blacksmith(self, args):
        s = self.settlement
        if not s.cities:
            self.add_message("Нет городов для постройки кузницы.")
            return
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
        price_per_unit = 3
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
        leaderboard = session.get('leaderboard', [])
        if not leaderboard:
            self.add_message("Таблица лидеров пуста. Стань первым!")
            return
        self.add_message("🏆 Таблица лидеров:")
        for i, entry in enumerate(leaderboard[:10], 1):
            self.add_message(f"{i}. {entry['name']} — грамот: {entry['charters']}, городов: {entry['cities']}")

    def check_game_over(self):
        s = self.settlement
        if len(s.living_travelers()) == 0 and len(s.all_alive()) == 0:
            self.add_message("💀 Все путешественники погибли. Игра окончена.")
            self.running = False
            return True
        if s.fur <= 0 and s.equipment <= 0 and s.season == 3:
            self.add_message("💀 Зимой одновременно закончились пушнина и экипировка – нечем кормить и греть людей. Все погибли от голода и холода. Игра окончена.")
            self.running = False
            return True
        if s.charters >= 100:
            self.add_message("🏙️ ВЕЛИКАЯ ПОБЕДА! Ты накопил 100 грамот, стал великим князем Сибири, и город назван в твою честь! Ты вошёл в историю как величайший первопроходец!")
            self.running = False
            return True
        return False

    def cmd_quit(self, args):
        self.add_message("Выход из игры.")
        self.running = False


# =================================================================
# МЕНЕДЖЕР СОБЫТИЙ
# =================================================================

class EventManager:
    def __init__(self, game):
        self.game = game

    def random_event(self):
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
            self.event_china_border,
        ]
        choice = random.choice(events)
        choice()

    def random_event_after_expedition(self, participants):
        if random.random() < 0.08:
            self.event_injury(participants)

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
                self.game.add_message("🙏 Шаман принял православие! В благодарность он дарит вам экипировку и указывает места, богатые пушниной.")
                bonus_equip = random.randint(10, 30)
                self.game.settlement.equipment += bonus_equip
                self.game.add_message(f"Получено {bonus_equip} экипировки.")
                self.game.hunting_boost = True
                self.game.hunting_boost_multiplier = random.uniform(1.5, 2.0)
                self.game.add_message("Следующая экспедиция принесёт значительно больше пушнины!")
            else:
                self.game.add_message("Шаман не поддался на уговоры, но предложил вам обменяться дарами.")
                gift = random.randint(5, 15)
                self.game.settlement.fur += gift
                self.game.add_message(f"Вы получили {gift} пушнины в качестве дара.")
        else:
            self.game.add_message("Неверный ввод. Попробуй ещё раз.")
            self.event_tribe_shaman()

    def event_tribe_marriage(self):
        s = self.game.settlement
        living = s.living_travelers()
        if len(living) < 2:
            return
        groom = random.choice(living)
        s.travelers.remove(groom)
        self.game.add_message(f"💒 {groom.name} женился на местной девушке и решил остаться в племени. Он покидает отряд.")
        gift = random.randint(10, 30)
        s.money += gift
        self.game.add_message(f"Племя дарит вам {gift} рублей в качестве приданого.")

    def event_injury(self, participants):
        s = self.game.settlement
        if not participants:
            return
        victim = random.choice(participants)
        doctor = None
        for t in participants:
            if t.is_doctor and t != victim and t.alive and t.injured_until_season == -1:
                doctor = t
                break
        if doctor:
            caretaker = doctor
        else:
            others = [t for t in s.living_travelers() if t != victim]
            if not others:
                return
            caretaker = random.choice(others)
        victim.injured_until_season = 2
        caretaker.injured_until_season = 2
        s.injured_travelers.append((victim.name, 2, caretaker.name))
        self.game.add_message(f"🦴 {victim.name} сломал ногу во время похода. {caretaker.name} остаётся с ним на два сезона.")

    def event_china_border(self):
        s = self.game.settlement
        if s.lands >= 5 and not self.game.china_discovered and random.random() < 0.04:
            self.game.china_discovered = True
            city = City("Пограничная застава")
            city.is_frontier = True
            city.trade_bonus = 10
            s.cities.append(city)
            s.city_names.append("Пограничная застава")
            self.game.add_message("🇨🇳 Ваш отряд достиг границы с Китаем! Основана пограничная застава. Теперь купцы могут торговать чаем, принося дополнительный доход.")


# =================================================================
# FLASK ПРИЛОЖЕНИЕ
# =================================================================

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
        if 'leaderboard' not in session:
            session['leaderboard'] = []
        return redirect(url_for('index'))

    if 'game_state' in session:
        game = pickle.loads(session['game_state'])
        game.ensure_attributes()

        if request.method == 'POST' and 'command' in request.form:
            command = request.form.get('command', '').strip().lower()
            if command:
                game.process_command(command)
                session['game_state'] = pickle.dumps(game)

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

@app.route('/add_leaderboard', methods=['POST'])
def add_leaderboard():
    data = request.get_json()
    name = data.get('name', '')
    charters = data.get('charters', 0)
    cities = data.get('cities', 0)
    leaderboard = session.get('leaderboard', [])
    leaderboard.append({'name': name, 'charters': charters, 'cities': cities})
    leaderboard.sort(key=lambda x: x['charters'], reverse=True)
    session['leaderboard'] = leaderboard[:10]
    return {'status': 'ok'}

if __name__ == '__main__':
    app.run(debug=True)
