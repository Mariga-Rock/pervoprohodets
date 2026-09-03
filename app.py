import random
import json
import os
import uuid
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
        self.poisoned_until_season = -1
        self.scurvy_treatment_offered = False
        self.scurvy_healer_offered = False
        self.wound_level = 0
        self.wound_heal_seasons = 0

    def ensure_attributes(self):
        if not hasattr(self, 'is_doctor'):
            self.is_doctor = random.random() < 0.1
        if not hasattr(self, 'is_scientist'):
            self.is_scientist = random.random() < 0.1
        if not hasattr(self, 'injured_until_season'):
            self.injured_until_season = -1
        if not hasattr(self, 'injured_with'):
            self.injured_with = None
        if not hasattr(self, 'poisoned_until_season'):
            self.poisoned_until_season = -1
        if not hasattr(self, 'scurvy_treatment_offered'):
            self.scurvy_treatment_offered = False
        if not hasattr(self, 'scurvy_healer_offered'):
            self.scurvy_healer_offered = False
        if not hasattr(self, 'wound_level'):
            self.wound_level = 0
        if not hasattr(self, 'wound_heal_seasons'):
            self.wound_heal_seasons = 0


class City:
    ICONS = [
        '🏰', '🏯', '🏛️', '🏗️', '🏘️', '🏡', '🏠', '🏢', '🏣', '🏤',
        '🏥', '🏦', '🏨', '🏩', '🏪', '🏫', '🏬', '🏭', '🏯', '🏰'
    ]

    def __init__(self, name, river=None, icon=None):
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
        self.icon = icon

    def ensure_attributes(self):
        if not hasattr(self, 'icon') or self.icon is None:
            self.icon = random.choice(self.ICONS)


class Achievement:
    GOALS = [
        {"id": "first_city", "name": "Основать первый город", "reward": "бонус к обороне"},
        {"id": "fur_1000", "name": "Добыть 1000 пушнины", "reward": "доступ к царскому двору"},
        {"id": "artifacts_5", "name": "Найти 5 артефактов", "reward": "+5% к добыче"},
        {"id": "cure_all", "name": "Вылечить всех больных цингой", "reward": "повышение морали"},
        {"id": "isker_taken", "name": "Взять Искер", "reward": "титул 'Покоритель Искера'"},
        {"id": "kuchum_defeated", "name": "Победить Кучюма", "reward": "титул 'Победитель Кучюма'"},
        {"id": "tsar_favor_50", "name": "Достичь 50 царской милости", "reward": "+1 грамота"},
        {"id": "heal_50_wounds", "name": "Вылечить 50 раненых", "reward": "титул 'Полевой хирург'"},
        {"id": "survive_epidemic", "name": "Пережить эпидемию с потерями <10%", "reward": "титул 'Победитель эпидемии'"},
    ]

    def __init__(self):
        self.completed = set()
        self.discoveries = []
        self.wounds_healed = 0
        self.epidemic_survived = False

    def ensure_attributes(self):
        if not hasattr(self, 'completed'):
            self.completed = set()
        if not hasattr(self, 'discoveries'):
            self.discoveries = []
        if not hasattr(self, 'wounds_healed'):
            self.wounds_healed = 0
        if not hasattr(self, 'epidemic_survived'):
            self.epidemic_survived = False

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
        if not self.is_completed("isker_taken") and game.isker_taken:
            self.complete("isker_taken", game, "🏴 Ты взял Искер – столицу Сибири! Ты – Покоритель Искера.")
            game.add_tsar_favor(20)
        if not self.is_completed("kuchum_defeated") and game.kuchum_defeated:
            self.complete("kuchum_defeated", game, "🏹 Ты победил Кучюма! Сибирь свободна от его ига.")
        if not self.is_completed("tsar_favor_50") and game.settlement.tsar_favor >= 50:
            self.complete("tsar_favor_50", game, "👑 Царь доволен тобой! Ты получил 1 грамоту.")
            s.charters += 1
        if not self.is_completed("heal_50_wounds") and self.wounds_healed >= 50:
            self.complete("heal_50_wounds", game, "🩺 Ты вылечил 50 раненых! Ты – Полевой хирург.")
        if not self.is_completed("survive_epidemic") and self.epidemic_survived:
            self.complete("survive_epidemic", game, "💊 Ты пережил эпидемию цинги с минимальными потерями! Ты – Победитель эпидемии.")

    def is_completed(self, goal_id):
        return goal_id in self.completed

    def complete(self, goal_id, game, message):
        if goal_id not in self.completed:
            self.completed.add(goal_id)
            game.add_message(message)
            game.add_message("🏆 Достижение разблокировано!")

    def add_discovery(self, obj_type, name, comment=""):
        self.discoveries.append({"type": obj_type, "name": name, "comment": comment})


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
        self.flour = 200
        self.fish = 0
        self.pemmican = 0
        self.cranberries = 0
        self.is_first_winter = True
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
        self.drunkard_handled = False
        self.yasak_income = 0
        self.settlements = []
        self.settlement_lands = []
        self.land_icons = []
        self.morale = 100
        self.pine_needles = 0
        self.wild_garlic = 0
        self.herbs = 0
        self.bandages = 0
        self.honeysuckle_oil = 0
        self.stroganov_relation = 0
        self.discipline = 50
        self.kuchum_will = 100
        self.tsar_favor = 0

    def total_animals(self):
        return self.dogs + self.horses

    def living_travelers(self):
        result = []
        for t in self.travelers:
            if (t.alive and
                t.injured_until_season == -1 and
                t.poisoned_until_season == -1 and
                t.wound_level == 0):
                result.append(t)
        return result

    def all_alive(self):
        return [t for t in self.travelers if t.alive]

    def count_scurvy(self):
        return sum(1 for t in self.travelers if t.alive and t.scurvy)

    def has_scurvy(self):
        return self.count_scurvy() > 0

    def count_wounded(self):
        return sum(1 for t in self.travelers if t.alive and t.wound_level > 0)

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
        if not hasattr(self, 'flour'):
            self.flour = 200
        if not hasattr(self, 'fish'):
            self.fish = 0
        if not hasattr(self, 'pemmican'):
            self.pemmican = 0
        if not hasattr(self, 'cranberries'):
            self.cranberries = 0
        if not hasattr(self, 'is_first_winter'):
            self.is_first_winter = True
        if not hasattr(self, 'drunkard_handled'):
            self.drunkard_handled = False
        if not hasattr(self, 'yasak_income'):
            self.yasak_income = 0
        if not hasattr(self, 'settlements'):
            self.settlements = []
        if not hasattr(self, 'settlement_lands'):
            self.settlement_lands = []
        if not hasattr(self, 'land_icons'):
            self.land_icons = []
        if not hasattr(self, 'morale'):
            self.morale = 100
        if not hasattr(self, 'pine_needles'):
            self.pine_needles = 0
        if not hasattr(self, 'wild_garlic'):
            self.wild_garlic = 0
        if not hasattr(self, 'herbs'):
            self.herbs = 0
        if not hasattr(self, 'bandages'):
            self.bandages = 0
        if not hasattr(self, 'honeysuckle_oil'):
            self.honeysuckle_oil = 0
        if not hasattr(self, 'stroganov_relation'):
            self.stroganov_relation = 0
        if not hasattr(self, 'discipline'):
            self.discipline = 50
        if not hasattr(self, 'kuchum_will'):
            self.kuchum_will = 100
        if not hasattr(self, 'tsar_favor'):
            self.tsar_favor = 0
        for t in self.travelers:
            t.ensure_attributes()
        icons = City.ICONS
        for idx, city in enumerate(self.cities):
            if not hasattr(city, 'icon') or city.icon is None or city.icon not in icons:
                city.icon = icons[idx % len(icons)]
            if city.icon not in icons:
                city.icon = icons[idx % len(icons)]
            city.ensure_attributes()


class Game:
    RIVERS = [
        "Обь", "Иртыш", "Тобол", "Тавда", "Васюган", "Чулым", "Енисей",
        "Ангара", "Подкаменная Тунгуска", "Лена", "Витим", "Алдан", "Вилюй",
        "Колыма", "Индигирка", "Амур", "Сунгари", "Уссури", "Аргунь", "Шилка", "Зея"
    ]
    COAST_NORTH = [
        "Дальнегорск", "Терней", "Советская Гавань", "Николаевск-на-Амуре",
        "Охотск", "Аян", "Магадан"
    ]
    LAND_WEST = [
        "Дальнегорск", "Хабаровск", "Благовещенск", "Чита", "Иркутск",
        "Красноярск", "Томск", "Омск", "Тюмень", "Уфа"
    ]
    KHANS = [
        ("Кучум", "сибирские татары", "объединил окрестные улусы и взимает дань мехами со всех кочевий до самых гор."),
        ("Кодек", "татарское племя", "славится искусными всадниками и набегами на русские поселения."),
        ("Урус", "ногайцы", "кочует в степях и торгует с Бухарой."),
        ("Тайши", "калмыки", "исповедует буддизм, держит большие стада."),
        ("Хара-Хула", "тунгусы (эвенки)", "оленеводы и шаманы, почитают духов тайги."),
        ("Мамай", "остяки", "живут рыболовством, почитают реку как божество."),
        ("Субудай", "енисейские киргизы", "воинственное племя, платят дань соболями."),
        ("Байкал", "буряты", "живут на берегах Байкала, торгуют с китайцами."),
        ("Сарыг", "якуты", "скотоводы, знают толк в серебре и мехах."),
        ("Манчары", "юкагиры", "охотники на морского зверя, живут в землянках."),
        ("Тархан", "коряки", "воинственное племя, нападают на соседей."),
        ("Абылай", "казахи", "кочевники, платят ясак царю."),
        ("Шейбани", "узбеки", "торгуют с Бухарой и Китаем."),
        ("Кара", "чукчи", "живут на севере, охотятся на моржей."),
        ("Куба", "нивхи", "ловят рыбу на Амуре, знают целебные травы."),
        ("Сунгари", "маньчжуры", "торгуют с китайцами, сильны в военном деле."),
        ("Уссури", "удэгейцы", "искусные охотники и следопыты."),
        ("Аргунь", "эвенки", "живут в горах, знают месторождения руды."),
        ("Шилка", "тунгусы", "кочуют вдоль Амура."),
        ("Зея", "нанайцы", "славится рыболовством и торговлей."),
    ]

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
        self.royal_favor_seasons = 0
        self._settlement_people_count = 0
        self.river_index = 0
        self.phase = 0
        self.coast_index = 0
        self.land_return_index = 0
        self.ocean_choice_made = False
        self.healing_skill_level = 1
        self.healing_xp = 0
        self.collected_facts = []
        self.night_council_done = False
        self.isker_taken = False
        self.kuchum_defeated = False
        self.kara_ambush_done = False
        self.erman_alive = True
        self.epidemic_active = False
        self.epidemic_severity = 0
        self.wounded_list = []
        self.chronicle = []
        self.epidemic_handled = False
        self._reinforcement_coming = False
        self._reinforcement_seasons = 0

    def get_healing_level_name(self):
        names = {1: "Ученик", 2: "Подмастерье", 3: "Лекарь", 4: "Мастер-травник", 5: "Искусный целитель"}
        return names.get(self.healing_skill_level, "Ученик")

    def add_message(self, text):
        self.messages.append(text)

    def set_input_callback(self, callback, prompt):
        self.awaiting_input = True
        self.input_prompt = prompt
        self.input_callback = callback
        self.add_message(prompt)

    def advance_image(self):
        self.current_image_index = (self.current_image_index % 3) + 1

    def add_tsar_favor(self, delta):
        self.settlement.tsar_favor = max(-100, min(100, self.settlement.tsar_favor + delta))

    def add_stroganov_relation(self, delta):
        self.settlement.stroganov_relation = max(-100, min(100, self.settlement.stroganov_relation + delta))

    def add_discipline(self, delta):
        self.settlement.discipline = max(0, min(100, self.settlement.discipline + delta))

    def add_morale(self, delta):
        self.settlement.morale = max(0, min(100, self.settlement.morale + delta))

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
        if not hasattr(self, 'royal_favor_seasons'):
            self.royal_favor_seasons = 0
        if not hasattr(self, '_settlement_people_count'):
            self._settlement_people_count = 0
        if not hasattr(self, 'river_index'):
            self.river_index = 0
        if not hasattr(self, 'phase'):
            self.phase = 0
        if not hasattr(self, 'coast_index'):
            self.coast_index = 0
        if not hasattr(self, 'land_return_index'):
            self.land_return_index = 0
        if not hasattr(self, 'ocean_choice_made'):
            self.ocean_choice_made = False
        if not hasattr(self, 'healing_skill_level'):
            self.healing_skill_level = 1
        if not hasattr(self, 'healing_xp'):
            self.healing_xp = 0
        if not hasattr(self, 'collected_facts'):
            self.collected_facts = []
        if not hasattr(self, 'night_council_done'):
            self.night_council_done = False
        if not hasattr(self, 'isker_taken'):
            self.isker_taken = False
        if not hasattr(self, 'kuchum_defeated'):
            self.kuchum_defeated = False
        if not hasattr(self, 'kara_ambush_done'):
            self.kara_ambush_done = False
        if not hasattr(self, 'erman_alive'):
            self.erman_alive = True
        if not hasattr(self, 'epidemic_active'):
            self.epidemic_active = False
        if not hasattr(self, 'epidemic_severity'):
            self.epidemic_severity = 0
        if not hasattr(self, 'wounded_list'):
            self.wounded_list = []
        if not hasattr(self, 'chronicle'):
            self.chronicle = []
        if not hasattr(self, '_reinforcement_coming'):
            self._reinforcement_coming = False
        if not hasattr(self, '_reinforcement_seasons'):
            self._reinforcement_seasons = 0
        if not hasattr(self, 'epidemic_handled'):
            self.epidemic_handled = False
        self.achievements.ensure_attributes()
        self.settlement.ensure_attributes()

    # ================ МЕТОДЫ ДЛЯ НАВЫКА ЛЕЧЕНИЯ ================

    def add_healing_xp(self, amount):
        self.healing_xp += amount
        thresholds = {1:0, 2:30, 3:70, 4:120, 5:200}
        new_level = 1
        for lvl, xp_req in sorted(thresholds.items(), key=lambda x: x[1], reverse=True):
            if self.healing_xp >= xp_req:
                new_level = lvl
                break
        if new_level > self.healing_skill_level:
            self.healing_skill_level = new_level
            self.add_message(f"🩺 Ваш навык лечения повышен до уровня {self.healing_skill_level}!")
            if self.healing_skill_level == 2:
                self.add_message("Теперь вы можете лечить двух больных одновременно.")
            elif self.healing_skill_level == 3:
                self.add_message("Открыт рецепт отвара из горечавки и ольховых почек.")
            elif self.healing_skill_level == 4:
                self.add_message("Вы можете заготавливать хвою в любое время года.")
            elif self.healing_skill_level == 5:
                self.add_message("Вы достигли уровня Искусный целитель! Открыт «Стеллеров бальзам».")

    def add_fact(self, fact):
        if fact not in self.collected_facts:
            self.collected_facts.append(fact)
            self.add_message(f"📜 Новый факт: {fact}")

    def add_chronical(self, entry):
        self.chronicle.append(entry)
        self.add_message(f"📖 Летопись: {entry}")

    # ================ МЕТОДЫ ДЛЯ РЕК И ПУТЕШЕСТВИЯ ================

    def process_river_event(self):
        if self.phase == 0:
            if self.river_index < len(self.RIVERS):
                self._show_river_message(self.river_index)
                self.river_index += 1
            else:
                self.phase = 1
                self._show_ocean_choice()
        elif self.phase == 1:
            if not self.ocean_choice_made:
                self._show_ocean_choice()
            else:
                self.add_message("Вы уже достигли океана и сделали выбор.")
        elif self.phase == 2:
            if self.coast_index < len(self.COAST_NORTH):
                place = self.COAST_NORTH[self.coast_index]
                self.add_message(f"🌊 Ваш отряд достиг {place} на побережье Тихого океана.")
                self.settlement.money += 30
                self.coast_index += 1
                if self.coast_index == len(self.COAST_NORTH):
                    self.add_message("🏁 Вы достигли Магадана. Пора повернуть на юг.")
                    self.phase = 3
                    self.coast_index = len(self.COAST_NORTH) - 2
            else:
                self.phase = 3
                self.coast_index = len(self.COAST_NORTH) - 2
        elif self.phase == 3:
            if self.coast_index >= 0:
                place = self.COAST_NORTH[self.coast_index]
                self.add_message(f"🌊 Ваш отряд возвращается в {place}.")
                self.settlement.money += 20
                self.coast_index -= 1
                if self.coast_index < 0:
                    self.add_message("🏁 Вы вернулись в Дальнегорск. Путь лежит на запад.")
                    self.phase = 4
                    self.land_return_index = 1
            else:
                self.phase = 4
                self.land_return_index = 1
        elif self.phase == 4:
            if self.land_return_index < len(self.LAND_WEST):
                place = self.LAND_WEST[self.land_return_index]
                self.add_message(f"🚶 Ваш отряд достиг {place} на обратном пути.")
                if place == "Уфа":
                    self.add_message("🏆 Великое сибирское путешествие завершено! Вы вернулись в Уфу.")
                    self.phase = 5
                    self.check_epilogue()
                else:
                    self.settlement.money += 15
                    self.land_return_index += 1
            else:
                self.phase = 5
                self.check_epilogue()

    def _show_river_message(self, index):
        river = self.RIVERS[index]
        if index < len(self.KHANS):
            khan, tribe, info = self.KHANS[index]
        else:
            khan, tribe, info = "неизвестный", "неизвестное племя", "о котором мало что известно."
        self.add_message(f"🌊 Вы достигли реки {river}.")
        self.add_message(f"🏹 На берегах этой реки правит хан {khan} из племени {tribe}.")
        self.add_message(f"📜 О нём известно: {info}")
        self.settlement.money += 20
        self.add_fact(f"Достигнута река {river}, правление хана {khan}.")

    def _show_ocean_choice(self):
        self.add_message("🌅 Ваш отряд вышел к Тихому океану!")
        self.add_message("Что будешь делать?")
        self.add_message("  1 - Готовиться к мореплаванию")
        self.add_message("  2 - Исследовать побережье")
        self.add_message("  3 - Повернуть назад")
        self.set_input_callback(self._process_ocean_choice, "Твой выбор (1, 2 или 3): ")

    def _process_ocean_choice(self, choice):
        if choice == "1" or choice == "2":
            self.ocean_choice_made = True
            self.phase = 2
            self.coast_index = 0
            self.add_message("🚢 Начинаете исследование побережья.")
            self.process_river_event()
        elif choice == "3":
            self.ocean_choice_made = True
            self.phase = 4
            self.land_return_index = 1
            self.add_message("🔙 Поворачиваете назад.")
            self.process_river_event()
        else:
            self.add_message("❌ Неверный выбор.")
            self._show_ocean_choice()

    def check_epilogue(self):
        facts = len(self.collected_facts)
        skill = self.healing_skill_level
        self.add_message("📜 Эпилог:")
        self.add_message("Вы прошли путь Ермака – от разбойника до завоевателя Сибири. Ваше имя вписано в летописи.")
        if self.isker_taken:
            self.add_message("🏴 Вы водрузили знамя России над Искером.")
        if self.kuchum_defeated:
            self.add_message("🏹 Слепой Царь бежал в степи, и его власть сломлена.")
        if self.settlement.tsar_favor > 50:
            self.add_message("👑 Царь Иоанн лично благословил ваши труды.")
        if self.erman_alive:
            self.add_message("⚔️ Ермак Тимофеевич продолжает свой путь рядом с вами.")
        if facts > 20:
            self.add_message("📖 Ваши записи о народной медицине, как и труды Стеллера, станут вкладом в науку.")
        if skill >= 5:
            self.add_message("🩺 Вы превзошли самого Стеллера в искусстве врачевания.")
        self.add_message("🏆 Ваше дело продолжается – Сибирь открыта для новых подвигов!")

    # ================ ДИНАМИЧЕСКАЯ СЛОЖНОСТЬ ================

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
            self.add_message("💡 Подсказка: Лето — время экспедиций. Отправьте отряд за пушниной!")
            s.tutorial_step = 1
        elif step == 1 and s.fur > 0 and s.season == 2:
            self.add_message("💡 Подсказка: Осенью можно продать пушнину. Введи 'Продать пушнину <количество>'.")
            s.tutorial_step = 2
        elif step == 2 and s.equipment < 5 and s.money > 20:
            self.add_message("💡 Подсказка: Купите экипировку командой 'Купить экипировку <количество>'.")
            s.tutorial_step = 3
        elif step == 3 and s.season == 2 and s.cranberries == 0 and s.pine_needles == 0:
            self.add_message("💡 Подсказка: Осенью соберите клюкву или хвою – они помогут лечить цингу зимой.")
            s.tutorial_step = 4
        if len(s.cities) == 1 and not self.has_shown_tutorial("city"):
            self.add_message("💡 Подсказка: В городе можно построить храм и лечебницу.")
            self.mark_tutorial_shown("city")
        if s.charters >= 5 and not self.has_shown_tutorial("charter"):
            self.add_message("💡 Подсказка: У вас 5 грамот! Основать город можно командой 'Основать город <название>'.")
            self.mark_tutorial_shown("charter")
        if len(s.settlements) == 0 and s.lands >= 2 and len(s.living_travelers()) >= 4:
            self.add_message("💡 Подсказка: Основать казацкое поселение – доход и награда от царя.")
            self.mark_tutorial_shown("settlement")
        if self.healing_skill_level == 1 and self.healing_xp > 0:
            self.add_message("💡 Подсказка: Лечите цингу и раненых, чтобы повысить навык врачевания.")

    def has_shown_tutorial(self, key):
        return key in self.tutorial_messages_shown

    def mark_tutorial_shown(self, key):
        self.tutorial_messages_shown.add(key)

    # ================ ОБРАБОТКА КОМАНД ================

    def process_command(self, cmd):
        # Валидация команды
        if not cmd or len(cmd) > 200:
            self.add_message("Команда слишком длинная или пустая.")
            return self.messages
        allowed_chars = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?-()\"'")
        if any(c not in allowed_chars for c in cmd):
            self.add_message("Команда содержит недопустимые символы.")
            return self.messages

        self.messages = []
        if self.awaiting_input:
            self.awaiting_input = False
            if self.input_callback:
                self.input_callback(cmd)
            self.advance_image()
            return self.messages

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
            'собрать клюкву': self.cmd_gather_cranberries,
            'собрать хвою': self.cmd_gather_pine_needles,
            'собрать черемшу': self.cmd_gather_wild_garlic,
            'собрать травы': self.cmd_gather_herbs,
            'наловить рыбы': self.cmd_fish,
            'охота': self.cmd_hunt,
            'изготовить пеммикан': self.cmd_make_pemmican,
            'основать поселение': self.cmd_found_settlement,
            'карта': self.cmd_show_map,
            'открытия': self.cmd_show_discoveries,
            'отправить посольство в москву': self.cmd_send_embassy,
            'торговать с бухарой': self.cmd_trade_bukhara,
            'отправить разведчиков': self.cmd_send_scouts,
            'летопись': self.cmd_show_chronical,
            'казнить провинившегося': self.cmd_execute_discipline,
            'простить провинившегося': self.cmd_forgive_discipline,
            'лечить раненых': self.cmd_heal_wounded,
            'изолировать больных': self.cmd_isolate_sick,
            'связаться со строгановыми': self.cmd_contact_stroganov,
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
        s = self.settlement

        if not s.drunkard_handled:
            threshold = 3000 if s.church else 2000
            if s.money > threshold:
                self.event_drunkard()
                s.drunkard_handled = True

        for t in s.all_alive():
            if t.scurvy and not t.scurvy_treatment_offered:
                self.offer_initial_scurvy_treatment(t)
                break

        self.process_wounds()

        for city in s.cities:
            if city.is_frontier:
                s.money += city.trade_bonus
        if s.lands > 1:
            s.yasak_income = (s.lands - 1) * 5
            s.money += s.yasak_income
        s.money += len(s.settlements) * 10

        # Обработка подкреплений
        if self._reinforcement_coming:
            self._reinforcement_seasons -= 1
            if self._reinforcement_seasons <= 0:
                self._reinforcement_coming = False
                names = ["Семён", "Демид", "Артемий", "Прокопий", "Гаврила"]
                for _ in range(2):
                    name = random.choice(names) + " (подкрепление)"
                    new_t = Traveler(name)
                    self.settlement.travelers.append(new_t)
                self.add_message("🆕 Подкрепление прибыло! Два новых бойца присоединились к отряду.")
                self.add_chronical("Подкрепление прибыло из Москвы.")

        if s.morale <= 0:
            self.event_mutiny()

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
            self.add_message("👑 Царь жалует тебе дворянское звание.")
        if s.total_fur_sent_to_tsar >= 10000 and s.noble_title != 'вельможа':
            s.noble_title = 'вельможа'
            self.add_message("👑 Ты стал вельможей!")
        if len(s.cities) >= 15 and s.noble_title != 'граф':
            s.noble_title = 'граф'
            self.add_message("👑 Ты получил титул графа!")

        self.check_scripted_events()

    def process_wounds(self):
        for t in self.settlement.all_alive():
            if t.wound_level > 0:
                t.wound_heal_seasons -= 1
                if t.wound_heal_seasons <= 0:
                    if random.random() < 0.1:
                        t.alive = False
                        self.add_message(f"💀 {t.name} умер от ран.")
                    else:
                        t.wound_level = 0
                        self.add_message(f"🩹 {t.name} оправился от ран.")
        self.settlement.remove_dead()

    # ================ НОВЫЕ СКРИПТОВЫЕ СОБЫТИЯ ================

    def check_scripted_events(self):
        s = self.settlement
        if not self.night_council_done and s.lands >= 4 and s.season == 1:
            self.night_council_done = True
            self.event_night_council()
        if not self.isker_taken and s.lands >= 5:
            self.isker_taken = True
            self.event_take_isker()
        if s.tsar_favor < -20 and not hasattr(self, '_tsar_anger_triggered'):
            self._tsar_anger_triggered = True
            self.event_tsar_anger()
        if not self.kara_ambush_done and len(s.cities) >= 2 and random.random() < 0.15:
            self.kara_ambush_done = True
            self.event_kara_ambush()
        if self.erman_alive and s.lands >= 7 and random.random() < 0.05:
            self.event_erman_death()
        if (s.season == 3 or s.season == 0) and not self.epidemic_active:
            total_res = s.cranberries + s.pine_needles + s.wild_garlic
            if total_res < len(s.all_alive()) * 2 and random.random() < 0.3:
                self.start_epidemic()
        if s.discipline < 40 and random.random() < 0.1 and len(s.living_travelers()) > 3:
            self.event_mass_wounds()

    def start_epidemic(self):
        s = self.settlement
        self.epidemic_active = True
        sick_count = int(len(s.all_alive()) * random.uniform(0.3, 0.5))
        sick_people = random.sample([t for t in s.all_alive() if not t.scurvy], min(sick_count, len(s.all_alive())))
        for t in sick_people:
            t.scurvy = True
        self.epidemic_severity = sick_count
        self.add_message(f"🦠 В отряде вспыхнула эпидемия цинги! Заболело {sick_count} человек.")
        self.add_message("Что будешь делать?")
        self.add_message("  1 - Лечить всех больных (требует много ресурсов)")
        self.add_message("  2 - Лечить только тяжёлых (часть умрёт)")
        self.add_message("  3 - Изолировать больных (замедлит распространение)")
        self.add_message("  4 - Игнорировать (эпидемия усилится)")
        self.set_input_callback(self.process_epidemic_choice, "Твой выбор (1-4): ")

    def process_epidemic_choice(self, choice):
        s = self.settlement
        if choice == "1":
            cost = self.epidemic_severity * 2
            if s.cranberries + s.pine_needles + s.wild_garlic >= cost:
                use = cost
                if s.cranberries >= use:
                    s.cranberries -= use
                else:
                    use -= s.cranberries
                    s.cranberries = 0
                    if s.pine_needles >= use:
                        s.pine_needles -= use
                    else:
                        use -= s.pine_needles
                        s.pine_needles = 0
                        s.wild_garlic -= use
                for t in s.all_alive():
                    t.scurvy = False
                self.add_message("💊 Все больные вылечены! Эпидемия побеждена.")
                self.achievements.epidemic_survived = True
                self.add_healing_xp(20)
                self.epidemic_active = False
            else:
                self.add_message("❌ Недостаточно ресурсов. Придётся лечить только тяжёлых.")
                self.process_epidemic_choice("2")
        elif choice == "2":
            sick = [t for t in s.all_alive() if t.scurvy]
            if sick:
                heal_count = len(sick) // 2
                heal_list = random.sample(sick, heal_count)
                for t in heal_list:
                    t.scurvy = False
                for t in sick:
                    if t.scurvy:
                        t.alive = False
                s.remove_dead()
                self.add_message(f"💊 Вылечено {heal_count} человек, остальные умерли.")
                self.add_healing_xp(10)
                self.epidemic_active = False
        elif choice == "3":
            self.add_message("🏥 Больные изолированы. Эпидемия замедлена, но не остановлена.")
            self.epidemic_severity = max(1, self.epidemic_severity // 2)
            self.epidemic_handled = True
        elif choice == "4":
            deaths = random.randint(1, self.epidemic_severity)
            victims = random.sample([t for t in s.all_alive() if t.scurvy], min(deaths, len([t for t in s.all_alive() if t.scurvy])))
            for v in victims:
                v.alive = False
            s.remove_dead()
            self.add_message(f"💀 Эпидемия усилилась! Умерло {deaths} человек.")
            self.epidemic_active = False
        else:
            self.add_message("❌ Неверный выбор.")
            self.start_epidemic()

    def event_night_council(self):
        self.add_message("🌙 Ночной совет Козаков. Отряд устал, многие хотят повернуть назад.")
        self.add_message("Что делать?")
        self.add_message("  1 - Идти вперёд (риск, но слава)")
        self.add_message("  2 - Повернуть назад (сохранить отряд, потерять земли)")
        self.add_message("  3 - Отправить гонцов за подкреплением")
        self.set_input_callback(self.process_night_council, "Твой выбор (1-3): ")

    def process_night_council(self, choice):
        s = self.settlement
        if choice == "1":
            self.add_message("⚔️ Вы решаете идти вперёд! Мораль +10, дисциплина +5.")
            self.add_morale(10)
            self.add_discipline(5)
            self.add_chronical("Ночной совет: решено идти вперёд, несмотря на усталость.")
        elif choice == "2":
            self.add_message("🔙 Вы поворачиваете назад. Потеряно 2 земли, но отряд сохранён.")
            s.lands = max(1, s.lands - 2)
            self.add_morale(-5)
            self.add_chronical("Ночной совет: решено отступить, потеряно 2 земли.")
        elif choice == "3":
            self.add_message("📨 Отправлены гонцы. Шанс получить подкрепление через 2 сезона.")
            self._reinforcement_coming = True
            self._reinforcement_seasons = 2
            self.add_chronical("Ночной совет: отправлены гонцы за подкреплением.")
        else:
            self.add_message("❌ Неверный выбор.")
            self.event_night_council()

    def event_take_isker(self):
        self.add_message("🏰 Вы подошли к столице Сибири – Искеру. Город укреплён тройным валом.")
        self.add_message("Как брать?")
        self.add_message("  1 - Штурм (быстро, но потери)")
        self.add_message("  2 - Осада (долго, но безопасно)")
        self.add_message("  3 - Ночная вылазка (рискованно, но внезапно)")
        self.set_input_callback(self.process_take_isker, "Твой выбор (1-3): ")

    def process_take_isker(self, choice):
        s = self.settlement
        if choice == "1":
            losses = random.randint(5, 15)
            if len(s.living_travelers()) >= losses:
                victims = random.sample(s.living_travelers(), losses)
                for v in victims:
                    v.alive = False
                s.remove_dead()
                self.add_message(f"⚔️ Искер взят штурмом! Потеряно {losses} человек.")
                self.add_chronical("Искер взят штурмом, город пал.")
                self.isker_taken = True
                self.add_tsar_favor(20)
                self.add_discipline(10)
                s.money += 300
                self.add_message("💰 В городе найдено 300 рублей.")
            else:
                self.add_message("❌ Недостаточно людей для штурма. Попробуйте осаду.")
                self.event_take_isker()
        elif choice == "2":
            self.add_message("🛡️ Вы начали осаду. Город сдался через 2 сезона без потерь.")
            self.add_chronical("Искер взят осадой, без потерь.")
            self.isker_taken = True
            self.add_tsar_favor(10)
            s.money += 200
            self.add_message("💰 В городе найдено 200 рублей.")
        elif choice == "3":
            if random.random() < 0.6:
                self.add_message("🌙 Ночная вылазка удалась! Искер взят с минимальными потерями (2 человека).")
                victims = random.sample(s.living_travelers(), min(2, len(s.living_travelers())))
                for v in victims:
                    v.alive = False
                s.remove_dead()
                self.add_chronical("Искер взят ночной вылазкой, минимальные потери.")
                self.isker_taken = True
                self.add_tsar_favor(25)
                s.money += 400
                self.add_message("💰 В городе найдено 400 рублей.")
            else:
                self.add_message("💀 Ночная вылазка провалилась! Потеряно 10 человек, город не взят.")
                victims = random.sample(s.living_travelers(), min(10, len(s.living_travelers())))
                for v in victims:
                    v.alive = False
                s.remove_dead()
                self.add_chronical("Ночная вылазка на Искер провалилась, большие потери.")
        else:
            self.add_message("❌ Неверный выбор.")
            self.event_take_isker()

    def event_tsar_anger(self):
        self.add_message("👑 Царь гневается на ваше самовольство! Он требует объяснений.")
        self.add_message("Что делать?")
        self.add_message("  1 - Отправить посольство с дарами (Иван Кольцо)")
        self.add_message("  2 - Игнорировать (гнев усилится)")
        self.add_message("  3 - Написать письмо с объяснениями")
        self.set_input_callback(self.process_tsar_anger, "Твой выбор (1-3): ")

    def process_tsar_anger(self, choice):
        s = self.settlement
        if choice == "1":
            if any(t.name == "Иван Кольцо" for t in s.all_alive()):
                self.add_message("📨 Иван Кольцо отправлен в Москву с дарами. Через сезон он вернётся с наградой.")
                self.add_tsar_favor(30)
                self.add_chronical("Посольство Ивана Кольцо в Москву, гнев царя смягчён.")
                for t in s.travelers:
                    if t.name == "Иван Кольцо" and t.alive:
                        t.injured_until_season = 1
                        break
            else:
                self.add_message("❌ Иван Кольцо отсутствует в отряде. Придётся писать письмо.")
                self.process_tsar_anger("3")
        elif choice == "2":
            self.add_message("😤 Вы игнорируете гнев. Царь накладывает штраф: -2 грамоты, -200 рублей.")
            s.charters = max(0, s.charters - 2)
            s.money = max(0, s.money - 200)
            self.add_tsar_favor(-20)
            self.add_chronical("Царь наложил штраф за игнорирование его гнева.")
        elif choice == "3":
            self.add_message("📝 Вы пишете письмо с объяснениями. Гнев смягчён, но требует времени.")
            self.add_tsar_favor(10)
            self.add_chronical("Написано письмо царю с оправданиями.")
        else:
            self.add_message("❌ Неверный выбор.")
            self.event_tsar_anger()

    def event_kara_ambush(self):
        self.add_message("🤝 Карача приглашает вас в свой Улус для переговоров. Есть подозрение на засаду.")
        self.add_message("Что делать?")
        self.add_message("  1 - Отправить Ивана Кольцо (риск)")
        self.add_message("  2 - Отказаться (Карача станет врагом)")
        self.add_message("  3 - Отправить разведчиков (проверить)")
        self.set_input_callback(self.process_kara_ambush, "Твой выбор (1-3): ")

    def process_kara_ambush(self, choice):
        s = self.settlement
        if choice == "1":
            if any(t.name == "Иван Кольцо" for t in s.all_alive()):
                for t in s.travelers:
                    if t.name == "Иван Кольцо" and t.alive:
                        t.alive = False
                        break
                s.remove_dead()
                self.add_message("💀 Иван Кольцо попал в засаду и погиб! Отряд потерял лучшего атамана.")
                self.add_morale(-15)
                self.add_chronical("Иван Кольцо погиб в засаде Карачи.")
            else:
                self.add_message("❌ Ивана Кольцо нет в отряде. Отправьте разведчиков.")
                self.process_kara_ambush("3")
        elif choice == "2":
            self.add_message("🚫 Вы отказались. Карача становится врагом, но отряд в безопасности.")
            self.add_chronical("Отказ от переговоров с Карачой, он стал врагом.")
        elif choice == "3":
            if random.random() < 0.6:
                self.add_message("🕵️ Разведчики раскрыли засаду! Вы избежали ловушки.")
                self.add_chronical("Разведчики раскрыли засаду Карачи, удалось избежать потерь.")
                self.add_discipline(5)
            else:
                self.add_message("❌ Разведчики не вернулись. Засада удалась? Потери 3 человека.")
                victims = random.sample(s.living_travelers(), min(3, len(s.living_travelers())))
                for v in victims:
                    v.alive = False
                s.remove_dead()
                self.add_chronical("Разведчики пропали, засада Карачи привела к потерям.")
        else:
            self.add_message("❌ Неверный выбор.")
            self.event_kara_ambush()

    def event_erman_death(self):
        if not self.erman_alive:
            return
        self.add_message("⚰️ Ермак погиб в ночной схватке на берегу Иртыша! Отряд в трауре.")
        self.erman_alive = False
        for t in self.settlement.travelers:
            if t.name == "Ермак" and t.alive:
                t.alive = False
                break
        self.settlement.remove_dead()
        self.add_morale(-20)
        self.add_chronical("Гибель Ермака – великая потеря для отряда.")

    def event_mass_wounds(self):
        s = self.settlement
        living = s.living_travelers()
        if not living:
            return
        count = random.randint(2, min(5, len(living)))
        wounded = random.sample(living, count)
        for t in wounded:
            t.wound_level = random.randint(1, 2)
            t.wound_heal_seasons = 2 if t.wound_level == 2 else 1
        self.add_message(f"🩸 После битвы {count} человек ранены. Лечите их командой 'Лечить раненых'.")
        self.add_chronical(f"Массовое ранение {count} человек после битвы.")

    # ================ НОВЫЕ КОМАНДЫ ================

    def cmd_send_embassy(self, args):
        s = self.settlement
        if s.fur < 50:
            self.add_message("❌ У вас недостаточно пушнины для даров (нужно 50).")
            return
        if not self.erman_alive and not any(t.name == "Иван Кольцо" for t in s.all_alive()):
            self.add_message("❌ Нет подходящего посланника (Ермак или Иван Кольцо).")
            return
        messenger = None
        for t in s.all_alive():
            if t.name in ["Ермак", "Иван Кольцо"]:
                messenger = t
                break
        if not messenger:
            self.add_message("❌ Нет подходящего посланника.")
            return
        s.fur -= 50
        self.add_message(f"📨 {messenger.name} отправлен в Москву с 50 пушниной.")
        self.add_tsar_favor(20)
        self.add_chronical(f"Посольство во главе с {messenger.name} отправлено в Москву.")
        messenger.injured_until_season = 2

    def cmd_trade_bukhara(self, args):
        s = self.settlement
        if s.lands < 5:
            self.add_message("❌ Торговля с Бухарой доступна после освоения 5 земель.")
            return
        if s.fur < 20:
            self.add_message("❌ У вас мало пушнины для торговли (нужно 20).")
            return
        s.fur -= 20
        gold = random.randint(50, 150)
        s.money += gold
        self.add_message(f"🛍️ Обменяли 20 пушнины на {gold} рублей.")
        self.add_chronical(f"Торговля с Бухарой: получено {gold} рублей.")
        self.add_stroganov_relation(5)

    def cmd_send_scouts(self, args):
        living = self.settlement.living_travelers()
        if len(living) < 3:
            self.add_message("❌ Недостаточно людей для разведки (нужно 3).")
            return
        scouts = random.sample(living, 3)
        for t in scouts:
            t.injured_until_season = 1
        if random.random() < 0.6:
            self.add_message("🕵️ Разведчики вернулись с ценными сведениями.")
            self.bandit_activity = max(0.05, self.bandit_activity - 0.1)
            self.add_chronical("Успешная разведка, получены сведения о враге.")
        else:
            self.add_message("💀 Разведчики пропали без вести. Потеря 3 человек.")
            for t in scouts:
                t.alive = False
            self.settlement.remove_dead()
            self.add_chronical("Разведка провалилась, разведчики погибли.")

    def cmd_show_chronical(self, args):
        if not self.chronicle:
            self.add_message("📖 Летопись пока пуста.")
            return
        self.add_message("📖 Летопись подвигов:")
        for i, entry in enumerate(self.chronicle, 1):
            self.add_message(f"{i}. {entry}")

    def cmd_execute_discipline(self, args):
        s = self.settlement
        living = s.living_travelers()
        if not living:
            self.add_message("❌ Нет людей для казни.")
            return
        victim = random.choice(living)
        victim.alive = False
        s.remove_dead()
        self.add_discipline(10)
        self.add_morale(-5)
        self.add_message(f"⚔️ {victim.name} казнён за нарушение дисциплины. Дисциплина +10, мораль -5.")
        self.add_chronical(f"Казнь {victim.name} для поддержания дисциплины.")

    def cmd_forgive_discipline(self, args):
        self.add_discipline(-5)
        self.add_morale(5)
        self.add_message("🙏 Вы простили провинившегося. Дисциплина -5, мораль +5.")
        self.add_chronical("Прощение провинившегося, мораль повышена.")

    def cmd_heal_wounded(self, args):
        s = self.settlement
        wounded = [t for t in s.all_alive() if t.wound_level > 0]
        if not wounded:
            self.add_message("Нет раненых.")
            return
        total_need = sum(t.wound_level for t in wounded) * 2
        if s.herbs + s.bandages < total_need:
            self.add_message(f"❌ Недостаточно ресурсов для лечения всех раненых (нужно {total_need} трав/повязок).")
            return
        cost = total_need
        if s.herbs >= cost:
            s.herbs -= cost
        else:
            cost -= s.herbs
            s.herbs = 0
            s.bandages -= cost
        for t in wounded:
            t.wound_level = 0
            t.wound_heal_seasons = 0
        self.achievements.wounds_healed += len(wounded)
        self.add_message(f"💊 Вылечено {len(wounded)} раненых. Опыт врачевания +{len(wounded)*2}.")
        self.add_healing_xp(len(wounded) * 2)
        self.add_chronical(f"Вылечено {len(wounded)} раненых.")

    def cmd_isolate_sick(self, args):
        if not self.epidemic_active:
            self.add_message("Нет активной эпидемии.")
            return
        self.epidemic_severity = max(1, self.epidemic_severity // 2)
        self.add_message("🏥 Больные изолированы. Тяжесть эпидемии снижена.")
        self.add_chronical("Изоляция больных во время эпидемии.")

    def cmd_contact_stroganov(self, args):
        s = self.settlement
        if s.stroganov_relation < 0:
            self.add_message("❌ Отношения со Строгановыми плохие, они не отвечают.")
            return
        self.add_message("📨 Вы отправили запрос Строгановым. Они обещают помощь через сезон.")
        self.add_chronical("Запрошена помощь у Строгановых.")
        self.add_stroganov_relation(5)

    # ================ ЛЕЧЕНИЕ ЦИНГИ ================

    def offer_initial_scurvy_treatment(self, traveler):
        s = self.settlement
        options = []
        if s.cranberries > 0:
            options.append("1 - Съесть клюкву (лечит цингу)")
        if s.wild_garlic > 0:
            options.append("2 - Съесть черемшу")
        if s.pine_needles > 0:
            options.append("3 - Отвар хвои")
        if self.healing_skill_level >= 3 and s.herbs >= 2:
            options.append("4 - Отвар из горечавки и ольховых почек (2 травы, 90%)")
        if self.healing_skill_level >= 4 and s.pine_needles >= 1 and s.wild_garlic >= 1:
            options.append("5 - Сборный отвар (хвоя+черемша, 85%, +5 выносливости)")
        if self.healing_skill_level >= 5 and s.pine_needles >= 1 and s.wild_garlic >= 1 and s.cranberries >= 1:
            options.append("6 - Стеллеров бальзам (всё, 100%, +10 выносливости)")
        options.append("7 - Отказаться")
        msg = f"🫐 У {traveler.name} признаки цинги!\n"
        msg += "\n".join(options)
        self.add_message(msg)
        self.set_input_callback(lambda choice: self.process_scurvy_treatment_choice(traveler, choice),
                                "Твой выбор (1-7): ")

    def process_scurvy_treatment_choice(self, traveler, choice):
        s = self.settlement
        if choice == "1" and s.cranberries > 0:
            s.cranberries -= 1
            traveler.scurvy = False
            traveler.scurvy_treatment_offered = True
            self.add_message(f"🍒 {traveler.name} вылечен клюквой.")
            self.add_fact("Клюква – кладезь витамина С.")
            self.add_healing_xp(10)
        elif choice == "2" and s.wild_garlic > 0:
            s.wild_garlic -= 1
            traveler.scurvy = False
            traveler.scurvy_treatment_offered = True
            self.add_message(f"🧄 {traveler.name} вылечен черемшой.")
            self.add_fact("Черемша – дикий чеснок, лекарство от цинги.")
            self.add_healing_xp(10)
        elif choice == "3" and s.pine_needles > 0:
            s.pine_needles -= 1
            traveler.scurvy = False
            traveler.scurvy_treatment_offered = True
            self.add_message(f"🌿 {traveler.name} вылечен отваром хвои.")
            self.add_fact("Отвар хвои – средство камчатских аборигенов.")
            self.add_healing_xp(10)
        elif choice == "4" and self.healing_skill_level >= 3 and s.herbs >= 2:
            s.herbs -= 2
            if random.random() < 0.9:
                traveler.scurvy = False
                traveler.scurvy_treatment_offered = True
                self.add_message(f"🍵 {traveler.name} вылечен отваром горечавки.")
                self.add_fact("Г.В. Стеллер описал отвары горечавки.")
                self.add_healing_xp(15)
            else:
                self.add_message("Отвар не помог.")
        elif choice == "5" and self.healing_skill_level >= 4 and s.pine_needles >= 1 and s.wild_garlic >= 1:
            s.pine_needles -= 1
            s.wild_garlic -= 1
            if random.random() < 0.85:
                traveler.scurvy = False
                traveler.scurvy_treatment_offered = True
                traveler.endurance += 5
                self.add_message(f"🌿 {traveler.name} вылечен сборным отваром, +5 выносливости.")
                self.add_fact("Сборный отвар – мощное противоцинготное средство.")
                self.add_healing_xp(20)
            else:
                self.add_message("Сборный отвар не помог.")
        elif choice == "6" and self.healing_skill_level >= 5 and s.pine_needles >= 1 and s.wild_garlic >= 1 and s.cranberries >= 1:
            s.pine_needles -= 1
            s.wild_garlic -= 1
            s.cranberries -= 1
            traveler.scurvy = False
            traveler.scurvy_treatment_offered = True
            traveler.endurance += 10
            self.add_message(f"✨ {traveler.name} вылечен Стеллеровым бальзамом, +10 выносливости.")
            self.add_fact("Стеллеров бальзам – легендарный рецепт.")
            self.add_healing_xp(30)
        elif choice == "7":
            traveler.scurvy_treatment_offered = True
            self.add_message(f"😔 {traveler.name} отказался от лечения.")
        else:
            self.add_message("❌ Неверный выбор.")
            self.offer_initial_scurvy_treatment(traveler)

    def offer_healer_scurvy_treatment(self, traveler):
        s = self.settlement
        options = []
        if s.cranberries > 0:
            options.append("1 - Съесть клюкву (лечит цингу)")
        if s.wild_garlic > 0:
            options.append("2 - Съесть черемшу")
        if s.pine_needles > 0:
            options.append("3 - Отвар хвои")
        if self.healing_skill_level >= 3 and s.herbs >= 2:
            options.append("4 - Отвар из горечавки и ольховых почек (2 травы, 90%)")
        if self.healing_skill_level >= 4 and s.pine_needles >= 1 and s.wild_garlic >= 1:
            options.append("5 - Сборный отвар (хвоя+черемша, 85%, +5 выносливости)")
        if self.healing_skill_level >= 5 and s.pine_needles >= 1 and s.wild_garlic >= 1 and s.cranberries >= 1:
            options.append("6 - Стеллеров бальзам (всё, 100%, +10 выносливости)")
        options.append("7 - Отказаться")
        msg = f"🩺 Целитель предлагает помочь {traveler.name} с цингой!\n"
        msg += "\n".join(options)
        self.add_message(msg)
        self.set_input_callback(lambda choice: self._process_healer_scurvy_choice(traveler, choice),
                                "Твой выбор (1-7): ")

    def _process_healer_scurvy_choice(self, traveler, choice):
        s = self.settlement
        success = False
        if choice == "1" and s.cranberries > 0:
            s.cranberries -= 1
            traveler.scurvy = False
            traveler.scurvy_treatment_offered = True
            self.add_message(f"🍒 {traveler.name} вылечен клюквой при помощи целителя.")
            self.add_fact("Клюква – кладезь витамина С.")
            self.add_healing_xp(15)
            success = True
        elif choice == "2" and s.wild_garlic > 0:
            s.wild_garlic -= 1
            traveler.scurvy = False
            traveler.scurvy_treatment_offered = True
            self.add_message(f"🧄 {traveler.name} вылечен черемшой при помощи целителя.")
            self.add_fact("Черемша – дикий чеснок, лекарство от цинги.")
            self.add_healing_xp(15)
            success = True
        elif choice == "3" and s.pine_needles > 0:
            s.pine_needles -= 1
            traveler.scurvy = False
            traveler.scurvy_treatment_offered = True
            self.add_message(f"🌿 {traveler.name} вылечен отваром хвои с помощью целителя.")
            self.add_fact("Отвар хвои – средство камчатских аборигенов.")
            self.add_healing_xp(15)
            success = True
        elif choice == "4" and self.healing_skill_level >= 3 and s.herbs >= 2:
            s.herbs -= 2
            if random.random() < 0.9:
                traveler.scurvy = False
                traveler.scurvy_treatment_offered = True
                self.add_message(f"🍵 {traveler.name} вылечен отваром горечавки (целитель помог).")
                self.add_fact("Г.В. Стеллер описал отвары горечавки.")
                self.add_healing_xp(20)
                success = True
            else:
                self.add_message("Отвар не помог, но целитель обещает попробовать ещё раз.")
                self.offer_healer_scurvy_treatment(traveler)
                return
        elif choice == "5" and self.healing_skill_level >= 4 and s.pine_needles >= 1 and s.wild_garlic >= 1:
            s.pine_needles -= 1
            s.wild_garlic -= 1
            if random.random() < 0.85:
                traveler.scurvy = False
                traveler.scurvy_treatment_offered = True
                traveler.endurance += 5
                self.add_message(f"🌿 {traveler.name} вылечен сборным отваром с помощью целителя, +5 выносливости.")
                self.add_fact("Сборный отвар – мощное противоцинготное средство.")
                self.add_healing_xp(25)
                success = True
            else:
                self.add_message("Сборный отвар не помог.")
                self.offer_healer_scurvy_treatment(traveler)
                return
        elif choice == "6" and self.healing_skill_level >= 5 and s.pine_needles >= 1 and s.wild_garlic >= 1 and s.cranberries >= 1:
            s.pine_needles -= 1
            s.wild_garlic -= 1
            s.cranberries -= 1
            traveler.scurvy = False
            traveler.scurvy_treatment_offered = True
            traveler.endurance += 10
            self.add_message(f"✨ {traveler.name} вылечен Стеллеровым бальзамом с благословения целителя, +10 выносливости.")
            self.add_fact("Стеллеров бальзам – легендарный рецепт.")
            self.add_healing_xp(35)
            success = True
        elif choice == "7":
            traveler.scurvy_treatment_offered = True
            self.add_message(f"😔 {traveler.name} отказался от лечения целителя.")
            return
        else:
            self.add_message("❌ Неверный выбор. Попробуйте ещё раз.")
            self.offer_healer_scurvy_treatment(traveler)
            return

        if success:
            self.add_message("🙏 Целитель благословляет отряд! Мораль +5.")
            self.add_morale(5)

    # ================ ОСНОВАНИЕ ГОРОДА И ВЫБОР ГРАМОТ ================

    def cmd_found_city(self, args):
        s = self.settlement
        required = 5 + len(s.cities) * 5
        if s.charters < required:
            self.add_message(f"❌ Для основания следующего города нужно {required} грамот, а у тебя только {s.charters}.")
            return
        if not args:
            self.add_message("Укажите название города: команда 'Основать город <название>'")
            self.set_input_callback(self.create_city_with_name, "Введите название города: ")
            return
        city_name = " ".join(args).strip()
        if not city_name or len(city_name) > 30:
            self.add_message("Название города должно быть от 1 до 30 символов.")
            return
        if not all(c.isalnum() or c.isspace() or c in "-" for c in city_name):
            self.add_message("Название города содержит недопустимые символы.")
            return
        self._create_city(city_name)

    def create_city_with_name(self, city_name):
        if not city_name or city_name.strip() == "":
            self.add_message("Название не может быть пустым. Попробуйте снова командой 'Основать город'.")
            return
        city_name = city_name.strip()
        if len(city_name) > 30:
            self.add_message("Название слишком длинное (максимум 30 символов).")
            return
        if not all(c.isalnum() or c.isspace() or c in "-" for c in city_name):
            self.add_message("Название содержит недопустимые символы.")
            return
        self._create_city(city_name)

    def _create_city(self, city_name):
        s = self.settlement
        required = 5 + len(s.cities) * 5
        if s.charters < required:
            self.add_message(f"❌ Недостаточно грамот: нужно {required}, у тебя {s.charters}.")
            return
        s.charters -= required
        icons = City.ICONS
        icon_idx = len(s.cities) % len(icons)
        icon = icons[icon_idx]
        city = City(city_name, icon=icon)
        s.cities.append(city)
        s.city_names.append(city_name)
        self.add_message(f"{icon} Город {city_name} основан! Всего городов: {len(s.cities)}. Потрачено {required} грамот.")
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

    def offer_charter_choice(self):
        s = self.settlement
        self._charter_level = s.charters // 5
        self.add_message(f"\n🦅 Ты достиг {s.charters} царских грамот! Теперь у тебя есть выбор:")
        self.add_message("  1 - Основать город (потратить 5 грамот).")
        self.add_message("  2 - Получить двух новых путешественников в отряд (грамоты останутся).")
        self.set_input_callback(self.process_charter_choice, "Твой выбор (1 или 2): ")

    def process_charter_choice(self, choice):
        s = self.settlement
        level = self._charter_level
        if choice == "1":
            if s.charters >= 5:
                self.add_message("Введите название нового города:")
                self.set_input_callback(self.create_city_from_charter, "Название города: ")
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

    def create_city_from_charter(self, city_name):
        if not city_name or city_name.strip() == "":
            self.add_message("Название не может быть пустым. Попробуй снова через команду 'Основать город'.")
            return
        city_name = city_name.strip()
        if len(city_name) > 30:
            self.add_message("Название слишком длинное (максимум 30 символов).")
            return
        if not all(c.isalnum() or c.isspace() or c in "-" for c in city_name):
            self.add_message("Название содержит недопустимые символы.")
            return
        self._create_city(city_name)

    # ================ ОСТАЛЬНЫЕ КОМАНДЫ ================

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
            icons = ['🌲', '🌳', '🏔️', '🌾', '🏝️', '🌋', '🗻', '🧊']
            s.land_icons.append(random.choice(icons))
            gold = 50 + (s.lands - 1) * 10
            s.money += gold
            self.add_message(f"👑 Царь жалует {gold} золотых монет за присоединение новой земли!")
            if random.random() < 0.18:
                self.trigger_geographical_discovery()
            self.process_river_event()

        total_hunting = sum(t.hunting for t in chosen)
        synergy = self.synergy_multiplier(count)
        base_fur = total_hunting * 2 * synergy
        land_bonus = 1 + 0.1 * s.lands
        penalty = max(0, 1 - s.penalty_next_season / 100.0)
        animal_bonus = 1 + 0.05 * s.total_animals()
        random_factor = random.uniform(0.8, 1.2)
        perm_bonus = s.hunting_bonus_permanent
        shaman_bonus = 1.0
        if self.hunting_boost:
            shaman_bonus = self.hunting_boost_multiplier
            self.hunting_boost = False
            self.hunting_boost_multiplier = 1.0
        fur_gained = int(base_fur * land_bonus * animal_bonus * penalty * random_factor * perm_bonus * shaman_bonus)
        if fur_gained < 0:
            fur_gained = 0

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
        if amount <= 0:
            self.add_message("Количество должно быть положительным.")
            return
        if amount > 1000:
            self.add_message("Слишком большое количество.")
            return
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
        if count > 20:
            self.add_message("Слишком много собак.")
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
        if count > 20:
            self.add_message("Слишком много лошадей.")
            return
        total_cost = count * 50
        if s.money < total_cost:
            self.add_message(f"Недостаточно денег. Нужно {total_cost} руб., есть {s.money}.")
            return
        s.money -= total_cost
        s.horses += count
        self.add_message(f"🐎 Куплено {count} лошадей. Всего лошадей: {s.horses}")

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
        self.add_message(f"🏛️ В городе {target.name} построен храм! Теперь порог пьянства повышен до 3000 рублей.")

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
        if amount <= 0:
            self.add_message("Сумма должна быть положительной.")
            return
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
            self.add_message("Укажите сумму для пожертвования на помощь бедным.")
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
        if not s.benefactor:
            s.benefactor = True
            self.add_message("❤️ Твою помощь сирым и убогим будет помнить вся Сибирь!")
        else:
            self.add_message("❤️ Ты уже благотворитель. Дополнительное пожертвование принято с благодарностью.")
        self.add_message(f"Пожертвовано {amount} рублей на помощь нуждающимся.")

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
        if s.fish >= 2:
            s.fish -= 2
            self.add_message("🥬 Потрачено 2 кг рыбы на пропитание.")
        elif s.pemmican >= 2:
            s.pemmican -= 2
            self.add_message("🥩 Потрачено 2 кг пеммикана.")
        else:
            self.add_message("⚠️ Нет провизии для пропуска года, но ты переживаешь, хотя и голодным.")
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

    def cmd_help(self, args):
        self.add_message(self.get_help_text())

    def get_help_text(self):
        return """
Список команд:

  Отправиться за пушниной [кол-во] [регион] – летняя экспедиция
  Продать пушнину <кол-во> – продать пушнину (только осенью)
  Послать пушнину в царскую казну <кол-во> – 100 пушнины = 1 грамота
  Купить экипировку <кол-во> – купить экипировку
  Купить собаку [кол-во] – купить собак (50 руб/шт)
  Купить лошадь [кол-во] – купить лошадей (50 руб/шт)
  Построить храм – построить храм (500 руб)
  Построить частокол – защита от разбойников (100 руб)
  Построить кузницу – если есть железная руда (200 руб)
  Подкупить разбойников <сумма> – снизить активность
  Послать деньги семье <сумма> – отправить деньги семье
  Основать город <название> – требует 5+5*число_городов грамот
  Спонсировать научные исследования <сумма> – стать меценатом (≥200 руб)
  Пожертвовать сирым <сумма> – стать благотворителем
  Показать статус – состояние отряда
  Следующий сезон – перейти к следующему сезону
  Переждать до следующей весны – пропустить год (50 руб + 2 кг провизии)
  Города – информация о городах
  Лидеры – таблица лидеров
  Карта – карта земель
  Открытия – географические открытия
  Основать поселение – казацкое поселение
  Отправить посольство в Москву – посольство с дарами
  Торговать с Бухарой – торговля
  Отправить разведчиков – разведка
  Летопись – летопись подвигов
  Казнить провинившегося – повысить дисциплину
  Простить провинившегося – повысить мораль
  Лечить раненых – лечение раненых
  Изолировать больных – при эпидемии
  Связаться со Строгановыми – запрос помощи
  Помощь – эта справка
  Выход – выйти
        """

    def cmd_quit(self, args):
        self.add_message("Выход из игры.")
        self.running = False

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
            lines.append(f"{city.icon if city.icon else '🏙️'} {city.name} (река {city.river})")
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
        # Используем глобальный словарь leaderboard из сессии (через Flask)
        leaderboard = session.get('leaderboard', [])
        if not leaderboard:
            self.add_message("Таблица лидеров пуста. Стань первым!")
            return
        self.add_message("🏆 Таблица лидеров:")
        for i, entry in enumerate(leaderboard[:10], 1):
            self.add_message(f"{i}. {entry['name']} — грамот: {entry['charters']}, городов: {entry['cities']}")

    def cmd_gather_cranberries(self, args):
        s = self.settlement
        if s.season != 2:
            self.add_message("❌ Клюкву можно собирать только осенью!")
            return
        living = s.living_travelers()
        if not living:
            self.add_message("Нет здоровых людей для сбора клюквы.")
            return
        gathered = sum(random.randint(2, 5) for _ in living)
        s.cranberries += gathered
        self.add_message(f"🍒 Собрано {gathered} кг клюквы. Теперь в запасе {s.cranberries} кг.")
        if random.random() < 0.25:
            self.add_message("🏴 На сборщиков напали разбойники!")
            loss = gathered // 2
            if loss > 0:
                s.cranberries -= loss
                self.add_message(f"Разбойники отняли {loss} кг клюквы. Осталось {s.cranberries} кг.")
            if random.random() < 0.3:
                victim = random.choice(living)
                victim.alive = False
                self.add_message(f"⚔️ Разбойники убили {victim.name}.")
                s.remove_dead()

    def cmd_gather_pine_needles(self, args):
        s = self.settlement
        living = s.living_travelers()
        if not living:
            self.add_message("Нет здоровых людей для сбора хвои.")
            return
        if s.season == 3:
            gathered = sum(random.randint(1, 3) for _ in living)
        else:
            gathered = sum(random.randint(3, 6) for _ in living)
        s.pine_needles += gathered
        self.add_message(f"🌲 Собрано {gathered} кг хвои. Теперь в запасе {s.pine_needles} кг.")
        self.add_healing_xp(2 * gathered)

    def cmd_gather_wild_garlic(self, args):
        s = self.settlement
        if s.season != 1 and s.season != 2:
            self.add_message("❌ Черемшу можно собирать только летом и осенью!")
            return
        living = s.living_travelers()
        if not living:
            self.add_message("Нет здоровых людей для сбора черемши.")
            return
        gathered = sum(random.randint(2, 5) for _ in living)
        s.wild_garlic += gathered
        self.add_message(f"🧄 Собрано {gathered} кг черемши. Теперь в запасе {s.wild_garlic} кг.")
        self.add_healing_xp(2 * gathered)

    def cmd_gather_herbs(self, args):
        s = self.settlement
        if s.season != 1 and s.season != 2:
            self.add_message("❌ Лекарственные травы можно собирать только летом и осенью!")
            return
        living = s.living_travelers()
        if not living:
            self.add_message("Нет здоровых людей для сбора трав.")
            return
        gathered = sum(random.randint(1, 3) for _ in living)
        s.herbs += gathered
        self.add_message(f"🌿 Собрано {gathered} единиц лекарственных трав. Теперь в запасе {s.herbs}.")
        self.add_healing_xp(3 * gathered)

    def cmd_fish(self, args):
        s = self.settlement
        if s.season != 1:
            self.add_message("❌ Рыбачить можно только летом!")
            return
        living = s.living_travelers()
        if not living:
            self.add_message("Нет здоровых людей для рыбалки.")
            return
        caught = sum(random.randint(5, 15) for _ in living)
        s.fish += caught
        self.add_message(f"🐟 Поймано {caught} кг рыбы. Всего рыбы: {s.fish} кг.")

    def cmd_hunt(self, args):
        s = self.settlement
        living = s.living_travelers()
        if not living:
            self.add_message("Нет здоровых людей для охоты.")
            return
        if s.season == 3:
            modifier = 0.5
        elif s.season == 0:
            modifier = 0.7
        else:
            modifier = 1.0
        hunted = sum(random.randint(5, 15) for _ in living)
        hunted = int(hunted * modifier)
        s.pemmican += hunted
        self.add_message(f"🍖 Добыто {hunted} кг мяса (переработано в пеммикан). Всего пеммикана: {s.pemmican} кг.")

    def cmd_make_pemmican(self, args):
        self.add_message("ℹ️ Охота уже даёт пеммикан напрямую. Используй команду 'Охота'.")

    def cmd_found_settlement(self, args):
        s = self.settlement
        if len(s.cities) < 2 and not (len(s.cities) >= 1 and s.lands >= 5):
            self.add_message("❌ Нужно как минимум 2 города (или 1 город и 5 земель) для основания поселения.")
            return
        if len(s.living_travelers()) < 6:
            self.add_message("❌ В отряде должно быть не менее 6 здоровых людей.")
            return
        if len(s.settlements) >= 3:
            self.add_message("❌ Уже основано 3 поселения (максимум).")
            return
        self.add_message("Сколько человек отправить в поселение? (минимум 2, максимум половина отряда)")
        max_people = len(s.living_travelers()) // 2
        self.set_input_callback(lambda count: self.process_settlement_people(count, max_people),
                                f"Введите число (2-{max_people}): ")

    def process_settlement_people(self, count_str, max_people):
        try:
            count = int(count_str)
        except:
            self.add_message("❌ Неверное число. Попробуй ещё раз.")
            return
        s = self.settlement
        if count < 2 or count > max_people:
            self.add_message(f"❌ Число должно быть от 2 до {max_people}.")
            return
        if count > len(s.living_travelers()):
            self.add_message("❌ Недостаточно здоровых людей.")
            return
        self._settlement_people_count = count
        self.add_message(f"На какой земле основать поселение? (доступны земли 1-{s.lands})")
        self.set_input_callback(self.process_settlement_land, "Введите номер земли: ")

    def process_settlement_land(self, land_str):
        try:
            land = int(land_str)
        except:
            self.add_message("❌ Неверное число. Попробуй ещё раз.")
            return
        s = self.settlement
        if land < 1 or land > s.lands:
            self.add_message(f"❌ Доступны земли 1-{s.lands}.")
            return
        if land in s.settlement_lands:
            self.add_message("❌ На этой земле уже есть поселение.")
            return
        living = s.living_travelers()
        if len(living) < self._settlement_people_count:
            self.add_message("❌ Недостаточно здоровых людей.")
            return
        settlers = random.sample(living, self._settlement_people_count)
        for t in settlers:
            t.alive = False
        s.remove_dead()
        s.settlements.append(f"Поселение на земле {land}")
        s.settlement_lands.append(land)
        self.add_message(f"🏕️ Казацкое поселение основано на земле {land}! Отряд покинуло {self._settlement_people_count} человек.")
        self.give_settlement_reward()

    def give_settlement_reward(self):
        s = self.settlement
        rewards = [
            ("Золотая казна", lambda: self._reward_gold()),
            ("Царская грамота", lambda: self._reward_charter()),
            ("Земельный надел", lambda: self._reward_land()),
            ("Военное снаряжение", lambda: self._reward_equipment()),
            ("Дворянский чин", lambda: self._reward_noble()),
            ("Царское благоволение", lambda: self._reward_favor()),
        ]
        reward_name, reward_func = random.choice(rewards)
        result = reward_func()
        self.add_message(f"👑 Царь жалует тебе: {reward_name}! {result}")

    def _reward_gold(self):
        s = self.settlement
        gold = 300 + 50 * self._settlement_people_count
        s.money += gold
        return f"Получено {gold} рублей."

    def _reward_charter(self):
        s = self.settlement
        s.charters += 1
        return "Получена 1 грамота."

    def _reward_land(self):
        s = self.settlement
        s.yasak_income += 5
        return "Доход от ясака увеличен на 5 руб./сезон."

    def _reward_equipment(self):
        s = self.settlement
        amount = random.randint(20, 30)
        s.equipment += amount
        return f"Получено {amount} единиц экипировки."

    def _reward_noble(self):
        s = self.settlement
        if s.noble_title is None:
            s.noble_title = 'дворянин'
            return "Ты получил дворянский чин!"
        elif s.noble_title == 'дворянин':
            s.noble_title = 'барон'
            return "Ты стал бароном! (снижение порога пьянства на 200 руб.)"
        elif s.noble_title == 'барон':
            s.noble_title = 'граф'
            return "Ты стал графом! (ещё больше бонусов)"
        else:
            s.money += 500
            return "Ты уже достиг высшего титула, поэтому царь дарует 500 рублей."

    def _reward_favor(self):
        self.royal_favor_seasons += 5
        return "Царское благоволение! На 5 сезонов штрафы от пьянства снижены вдвое."

    def cmd_show_map(self, args):
        s = self.settlement
        if not s.land_icons:
            self.add_message("Карта пока пуста. Освой новые земли!")
            return
        map_str = "🗺️ Карта Сибири:\n"
        for i, icon in enumerate(s.land_icons):
            map_str += f"{icon} "
            if (i+1) % 10 == 0:
                map_str += "\n"
        self.add_message(map_str)

    def cmd_show_discoveries(self, args):
        if not self.achievements.discoveries:
            self.add_message("Пока нет географических открытий.")
            return
        self.add_message("🏆 Географические открытия:")
        for d in self.achievements.discoveries:
            comment = f" (пояснение: {d['comment']})" if d['comment'] else ""
            self.add_message(f"- {d['type']} «{d['name']}»{comment}")

    def trigger_geographical_discovery(self):
        obj_types = [
            ('🏞️', 'Река'),
            ('⛰️', 'Горный хребет'),
            ('🏔️', 'Плато'),
            ('🏝️', 'Озеро'),
            ('🌋', 'Вулкан'),
            ('🗻', 'Каньон'),
            ('🧊', 'Ледник'),
        ]
        obj_icon, obj_type = random.choice(obj_types)
        self.add_message(f"🌍 Ваш отряд обнаружил {obj_type}! Дайте ему название.")
        self.set_input_callback(lambda name: self.process_discovery_name(obj_type, obj_icon, name),
                                "Введите название: ")

    def process_discovery_name(self, obj_type, obj_icon, name):
        if not name or name.strip() == "":
            name = "Безымянный"
        self.add_message("Добавьте пояснение к открытию (необязательно, просто Enter, чтобы пропустить):")
        self.set_input_callback(lambda comment: self.finalize_discovery(obj_type, obj_icon, name, comment),
                                "Пояснение: ")

    def finalize_discovery(self, obj_type, obj_icon, name, comment):
        s = self.settlement
        self.achievements.add_discovery(obj_type, name, comment)
        s.charters += 1
        s.money += 50
        self.add_message(f"🏆 Открытие занесено в список! Получено: 1 грамота и 50 рублей.")
        self.add_message(f"📌 {obj_icon} {obj_type} «{name}»" + (f" (пояснение: {comment})" if comment else ""))

    def get_fur_price_modifier(self):
        s = self.settlement
        return max(0.5, 1 - (s.fur / 5000))

    def synergy_multiplier(self, count):
        if count <= 0: return 0
        if count == 1: return 1.0
        if count == 2: return 2.5
        if count == 3: return 7.5
        return 7.5 * (1.3 ** (count - 3))

    def advance_season(self):
        s = self.settlement
        s.drunkard_handled = False
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
        if s.season == 3:
            self.winter_consumption()
        if s.season == 0:
            s.year += 1
            self.merchant_price = random.randint(2, 10)
            self.add_message(f"🎉 Поздравляем! Ты занимаешься освоением Сибири в течение уже {s.year} лет.")
        self.event_manager.random_event()

    def winter_consumption(self):
        s = self.settlement
        living = s.living_travelers()
        if not living:
            return
        if s.is_first_winter and s.flour > 0:
            need = len(living) * 30
            if s.flour >= need:
                s.flour -= need
                self.add_message(f"❄️ Благодаря муке отряд пережил зиму. Осталось муки: {s.flour} кг.")
                s.is_first_winter = False
            else:
                self.add_message(f"❄️ Муки осталось {s.flour} кг, недостаточно.")
                s.flour = 0
                s.is_first_winter = False
        need = len(living) * 10
        total_food = s.fish + s.pemmican
        if total_food >= need:
            if s.fish >= need:
                s.fish -= need
            else:
                remain = need - s.fish
                s.fish = 0
                s.pemmican -= remain
            self.add_message(f"❄️ Зимой израсходовано {need} кг провизии.")
        else:
            deficit = need - total_food
            self.add_message(f"❄️ Зимой не хватило {deficit} кг провизии!")
            deaths = (deficit + 9) // 10
            deaths = min(deaths, len(living))
            if deaths > 0:
                victims = random.sample(living, deaths)
                for v in victims:
                    v.alive = False
                self.add_message(f"💀 От голода умерло {deaths} человек.")
                s.remove_dead()
            s.fish = 0
            s.pemmican = 0
        if s.cranberries > 0:
            cran_need = len(living)
            if s.cranberries >= cran_need:
                s.cranberries -= cran_need
                self.add_message(f"🍒 Зимой съедено {cran_need} кг клюквы. Осталось {s.cranberries} кг.")
            else:
                s.cranberries = 0
                self.add_message("🍒 Клюква кончилась.")
        if s.pine_needles > 0:
            pine_need = len(living)
            if s.pine_needles >= pine_need:
                s.pine_needles -= pine_need
                self.add_message(f"🌲 Зимой съедено {pine_need} кг хвои.")
            else:
                s.pine_needles = 0

    def check_game_over(self):
        s = self.settlement
        if len(s.living_travelers()) == 0 and len(s.all_alive()) == 0:
            self.add_message("💀 Все погибли. Игра окончена.")
            self.running = False
            return True
        if s.charters >= 100:
            self.add_message("🏙️ ВЕЛИКАЯ ПОБЕДА! 100 грамот!")
            self.running = False
            return True
        return False

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
        if s.settlements:
            lines.append(f"Казацких поселений: {len(s.settlements)}")
        lines.append(f"🍞 Мука: {s.flour} кг | 🐟 Рыба: {s.fish} кг | 🥩 Пеммикан: {s.pemmican} кг")
        lines.append(f"🍒 Клюква: {s.cranberries} кг | 🌲 Хвоя: {s.pine_needles} кг | 🧄 Черемша: {s.wild_garlic} кг | 🌿 Травы: {s.herbs} ед.")
        lines.append(f"💵 Ясак: {s.yasak_income} руб./сезон")
        lines.append(f"❤️ Мораль: {s.morale}%")
        lines.append(f"🩺 Врачевание: уровень {self.healing_skill_level} ({self.get_healing_level_name()}), XP: {self.healing_xp}/200")
        if self.collected_facts:
            lines.append(f"📜 Фактов: {len(self.collected_facts)}")
        if s.noble_title:
            lines.append(f"👑 Титул: {s.noble_title}")
        if s.stroganov_relation:
            lines.append(f"🏢 Строгановы: {s.stroganov_relation}")
        if s.discipline:
            lines.append(f"⚔️ Дисциплина: {s.discipline}")
        if s.tsar_favor:
            lines.append(f"👑 Царская милость: {s.tsar_favor}")
        if s.count_wounded():
            lines.append(f"🩸 Раненых: {s.count_wounded()}")
        if s.season == 2:
            price_mod = self.get_fur_price_modifier()
            lines.append(f"💰 Цена пушнины: {self.merchant_price * price_mod:.1f} руб./ед.")
        return "\n".join(lines)

    # ================ СОБЫТИЯ ПЬЯНСТВА, МУТИНИ, ДОЛГИ ================

    def event_drunkard(self):
        s = self.settlement
        threshold = 3000 if s.church else 2000
        self.add_message(f"🍺 Царь требует навести порядок! Денег: {s.money}, порог: {threshold}.")
        self.add_message("Что делаем?")
        self.add_message("  1 - Благотворительность (150 руб, +мораль)")
        self.add_message("  2 - Укрепить храм (500/100 руб)")
        self.add_message("  3 - Помочь семьям (100 руб)")
        self.add_message("  4 - Дисциплина (монастырь/лечебница/штраф)")
        self.add_message("  5 - Игнорировать")
        self.set_input_callback(self.process_drunkard_choice, "Выбор (1-5): ")

    def process_drunkard_choice(self, choice):
        s = self.settlement
        if choice == "1":
            if s.money >= 150:
                s.money -= 150
                if not s.benefactor:
                    s.benefactor = True
                    self.add_message("❤️ Ты стал благотворителем!")
                else:
                    self.add_message("❤️ Мораль повышена.")
                self.add_morale(5)
                s.drunkard_handled = True
            else:
                self.event_drunkard()
        elif choice == "2":
            target = None
            for city in s.cities:
                if not city.has_church:
                    target = city
                    break
            if target and s.money >= 500:
                s.money -= 500
                target.has_church = True
                self.add_message("🏛️ Храм построен.")
                s.drunkard_handled = True
            elif s.church and s.money >= 100:
                s.money -= 100
                self.add_message("🙏 Молебны проведены.")
                s.drunkard_handled = True
            else:
                self.event_drunkard()
        elif choice == "3":
            if s.money >= 100:
                s.money -= 100
                self.add_morale(3)
                self.add_message("📨 Деньги семьям.")
                s.drunkard_handled = True
            else:
                self.event_drunkard()
        elif choice == "4":
            self.add_message("Дисциплинарные меры:")
            self.add_message("  1 - Монастырь (нужен храм, 2 чел. на 2 сезона)")
            self.add_message("  2 - Лечебница (нужна лечебница, 1 чел. на 1 сезон)")
            self.add_message("  3 - Штраф (200 руб, -мораль)")
            self.set_input_callback(self.process_discipline_choice, "Выбор (1-3): ")
        elif choice == "5":
            s.money -= 500
            if s.charters > 0:
                s.charters -= 1
                self.add_message(f"😤 Потеря грамоты, осталось {s.charters}.")
            else:
                for t in s.all_alive():
                    t.endurance = max(1, t.endurance - 1)
                self.add_message("😤 Потеря выносливости.")
            s.drunkard_handled = True
        else:
            self.event_drunkard()

    def process_discipline_choice(self, subchoice):
        s = self.settlement
        if subchoice == "1":
            if any(c.has_church for c in s.cities):
                living = s.living_travelers()
                if len(living) >= 3:
                    victims = random.sample(living, 2)
                    for v in victims:
                        v.injured_until

