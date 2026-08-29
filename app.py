import random
import pickle
import os
from flask import Flask, request, render_template, session, redirect, url_for

# ============================ ИГРОВАЯ ЛОГИКА ============================
class Traveler:
    def __init__(self, name):
        self.name = name
        self.hunting = random.randint(3, 7)
        self.endurance = random.randint(3, 7)
        self.alive = True
        self.scurvy = False

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

    def total_animals(self):
        return self.dogs + self.horses

    def max_travelers(self):
        return len(self.travelers)

    def living_travelers(self):
        return [t for t in self.travelers if t.alive]

    def count_scurvy(self):
        return sum(1 for t in self.travelers if t.alive and t.scurvy)

    def has_scurvy(self):
        return self.count_scurvy() > 0

    def remove_dead(self):
        self.travelers = [t for t in self.travelers if t.alive]

    def add_traveler(self):
        if self.money >= 50:
            self.money -= 50
            new_t = Traveler("Новобранец")
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

    def add_message(self, text):
        self.messages.append(text)

    def set_input_callback(self, callback, prompt):
        self.awaiting_input = True
        self.input_prompt = prompt
        self.input_callback = callback
        self.add_message(prompt)

    def process_command(self, cmd):
        self.messages = []
        if self.awaiting_input:
            self.awaiting_input = False
            if self.input_callback:
                self.input_callback(cmd)
            return self.messages

        if not cmd:
            self.add_message("Введите команду.")
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
        return self.messages

    def after_action(self):
        self.check_debt()
        self.heal_scurvy_with_cabbage()
        s = self.settlement
        if s.charters >= 5:
            current_level = s.charters // 5
            if current_level > s.last_offer_level:
                self.offer_charter_choice()

    # --------------------- МЕТОДЫ ЛЕЧЕНИЯ И ПРОВЕРОК --------------------
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

    # --------------------- ВЫБОР ПРИ 5 ГРАМОТАХ ------------------------
    def offer_charter_choice(self):
        s = self.settlement
        self._charter_level = s.charters // 5
        self.add_message(f"\n🌟 Ты достиг {s.charters} царских грамот! Теперь у тебя есть выбор:")
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

    # --------------------- ОСНОВНЫЕ МЕТОДЫ ИГРЫ (CMD_*) -----------------
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

    def check_game_over(self):
        s = self.settlement
        if len(s.living_travelers()) == 0:
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

    # ----- КОМАНДЫ -----
    def cmd_help(self, args):
        self.add_message(self.get_help_text())

    def get_help_text(self):
        return """
Список команд:
  отправить <кол-во> <регион>          – экспедиция (только летом). Регион: 'новый' или номер.
  продать пушнину <кол-во>             – продать пушнину (только осенью).
  послать пушнину в царскую казну <кол-во> – за это государь пожалует тебе грамоту (100 = 1).
  купить экипировку <кол-во>           – купить экипировку (5 руб/ед).
  купить собаку [кол-во]               – купить собак (50 руб/шт).
  купить лошадь [кол-во]               – купить лошадей (50 руб/шт).
  купить квашеную капусту <кол-во>     – только осенью (10 руб/ед). Излечивает от цинги и спасает от зимнего голода.
  построить храм                       – полезно для прекращения пьянства и разгула (500 руб).
  построить частокол                   – спасает от разбойников (100 руб).
  подкупить разбойников <сумма>        – откупиться от разбойников на сезон.
  отправить семье <сумма>              – отправить деньги семье.
  основать город <название>            – основать город (требуется 5+5*число городов грамот).
  пожертвовать науке <сумма>           – пожертвовать на науку (≥200 руб) – статус мецената.
  пожертвовать сирым <сумма>           – пожертвовать на помощь сирым (≥150 руб) – статус благотворителя.
  статус                               – показать состояние.
  следующий сезон                      – перейти к следующему сезону.
  пропустить год                       – пропустить год (50 руб + 2 капусты).
  помощь                               – показать эту справку.
  выход                                – выйти.

Сезоны года:
  🌸 Весна – время подготовки к новому сезону. Можно закупать экипировку и животных.
  ☀️ Лето – основное время для экспедиций. Отправляй путешественников в новые земли или в уже открытые регионы. С приходом лета все больные цингой излечиваются!
  🍂 Осень – завершение охоты, подсчёт добычи. Только осенью можно продавать пушнину купцам и покупать квашеную капусту. Возможны набеги разбойников.
  ❄️ Зима – дальние походы невозможны. Тратится экипировка и пушнина на отопление и пропитание. Если запасы на исходе – люди гибнут, но только если нет достаточно квашеной капусты (1 капуста на каждого путешественника). Капуста спасает от голода!

⚠️ Пьянство и разгул наступают каждый раз, когда количество денег превышает 2000 рублей (или 3000, если построен храм).
        """

    def cmd_quit(self, args):
        self.add_message("Выход из игры.")
        self.running = False

    def cmd_status(self, args):
        self.display_status()

    def display_status(self):
        s = self.settlement
        season_names = ["🌸 Весна", "☀️ Лето", "🍂 Осень", "❄️ Зима"]
        self.add_message("\n" + "-"*50)
        self.add_message(f"Год {s.year}, сезон: {season_names[s.season]}")
        self.add_message(f"Путешественников: {len(s.living_travelers())} (всего {len(s.travelers)})")
        if s.has_scurvy():
            self.add_message(f"   (Цинга: {s.count_scurvy()} больных)")
        self.add_message(f"Пушнина: {s.fur} | Экипировка: {s.equipment} | Деньги: {s.money} руб.")
        self.add_message(f"Собаки/лошади: {s.dogs}/{s.horses} (всего {s.total_animals()})")
        self.add_message(f"Открытые земли: {s.lands} | Царские грамоты: {s.charters}")
        if s.city_names:
            self.add_message(f"Основанные города: {', '.join(s.city_names)} (всего {len(s.city_names)})")
        else:
            self.add_message("Основанные города: нет")
        if s.church:
            self.add_message("🏛️ Храм построен (порог пьянства +1000, помогает при долгах)")
        if s.palisade:
            self.add_message("🛡️ Частокол построен (защита от разбойников)")
        if s.cabbage > 0:
            self.add_message(f"🥬 Квашеная капуста: {s.cabbage}")
        if s.patron_of_science:
            self.add_message("🔬 Меценат (поддерживает науку)")
        if s.benefactor:
            self.add_message("❤️ Благотворитель (помогает сирым)")
        if s.penalty_next_season > 0:
            self.add_message(f"⚠️ Штраф к добыче: -{s.penalty_next_season}%")
        if s.season == 2:
            self.add_message(f"💰 Цена пушнины у купцов: {self.merchant_price} руб./ед. (можно продавать)")
        self.add_message("-"*50)

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
        self.add_message(f"⏩ Ты пропустил целый год! Теперь год {s.year}, сезон Весна.")
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
        revenue = amount * self.merchant_price
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
        self.add_message(f"👑 Отправлено {amount} пушнины в царскую казну. Царь пожаловал тебе {earned} грамот! Это высочайшая царская милость! Всего грамот: {s.charters}.")

    def cmd_expedition(self, args):
        if self.settlement.season != 1:
            self.add_message("❌ Экспедиции возможны только летом!")
            return
        if len(args) < 2:
            self.add_message("Использование: отправить <кол-во> <регион>")
            self.add_message("Регион: 'новый' или число от 1 до " + str(self.settlement.lands))
            return
        try:
            count = int(args[0])
        except:
            self.add_message("Неверное число.")
            return
        region = args[1]
        s = self.settlement
        living = s.living_travelers()
        if count > len(living):
            self.add_message(f"У вас только {len(living)} живых путешественников.")
            return
        if count <= 0:
            self.add_message("Нужно отправить хотя бы одного.")
            return
        is_new = (region == 'новый')
        extra_equip_cost = 5 if is_new else 0
        need_equip = count * 3 + extra_equip_cost
        if s.equipment < need_equip:
            self.add_message(f"Недостаточно экипировки. Нужно {need_equip}, есть {s.equipment}.")
            return
        if is_new:
            region_idx = s.lands + 1
        else:
            try:
                region_idx = int(region)
            except:
                self.add_message("Регион должен быть 'новый' или число.")
                return
            if region_idx < 1 or region_idx > s.lands:
                self.add_message(f"Доступны регионы от 1 до {s.lands} или 'новый'.")
                return
        s.equipment -= need_equip
        if is_new:
            self.add_message(f"🗺️ Открыта новая земля! Потрачено 5 дополнительных единиц экипировки.")
            s.lands += 1
            self.add_message(f"Теперь открытых земель: {s.lands}")
        total_hunting = sum(t.hunting for t in living[:count])
        synergy = self.synergy_multiplier(count)
        base_fur = total_hunting * 2 * synergy
        land_bonus = 1 + 0.1 * s.lands
        penalty = 1 - s.penalty_next_season / 100.0
        if penalty < 0: penalty = 0
        animal_bonus = 1 + 0.05 * s.total_animals()
        random_factor = random.uniform(0.8, 1.2)
        fur_gained = int(base_fur * land_bonus * animal_bonus * penalty * random_factor)
        if fur_gained < 0: fur_gained = 0
        # Встреча с разбойниками
        bandit_chance = 0.2 if not s.palisade else 0.1
        if random.random() < bandit_chance:
            self.add_message("\n🏴 ВНИМАНИЕ! На ваш отряд напали разбойники!")
            self.add_message("Что будешь делать?")
            self.add_message("  1 - Вступить в бой (риск потери выносливости, животных, пушнины и даже людей)")
            self.add_message("  2 - Откупиться (заплатить деньги, разбойники уйдут)")
            self._bandit_count = count
            self._bandit_living = living
            self._bandit_fur_gained = fur_gained
            self.set_input_callback(self.process_bandit_choice, "Твой выбор (1 или 2): ")
            return
        else:
            self.add_message("✅ Поход прошёл без нападений.")
        s.fur += fur_gained
        self.add_message(f"🦊 Добыто {fur_gained} пушнины.")
        s.penalty_next_season = 0

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
                if killed_in_battle == 1:
                    self.add_message("⚔️ В бою погиб 1 путешественник.")
                else:
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
        cost = amount * 5
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
        if s.cabbage == 0:
            self.add_message("Вся капуста ушла на лечение, запаса не осталось.")
        else:
            self.add_message(f"Теперь в запасе {s.cabbage} капусты.")

    def cmd_build_church(self, args):
        s = self.settlement
        if s.church:
            self.add_message("Храм уже построен.")
            return
        if s.money < 500:
            self.add_message("Недостаточно денег. Нужно 500 руб.")
            return
        s.money -= 500
        s.church = True
        self.add_message("🏛️ Храм построен! Теперь порог пьянства повышен до 3000 рублей, и при долгах можно обратиться за помощью.")

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
        required = 5 + len(s.city_names) * 5
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
        s.city_names.append(city_name)
        self.add_message(f"🏙️ Город {city_name} основан! Всего городов: {len(s.city_names)}. Потрачено {required} грамот.")

    def cmd_donate_science(self, args):
        if not args:
            self.add_message("Укажите сумму для пожертвования на науку.")
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
            self.add_message("Минимальное пожертвование на науку – 200 рублей.")
            return
        s.money -= amount
        if not s.patron_of_science:
            s.patron_of_science = True
            self.add_message("🔬 Ты стал меценатом! Наука в Сибири получит развитие. Спасибо за твой вклад!")
        else:
            self.add_message("🔬 Ты уже меценат. Но дополнительное пожертвование принято с благодарностью.")
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
            self.add_message("Минимальное пожертвование на помощь сирым – 150 рублей.")
            return
        s.money -= amount
        if not s.benefactor:
            s.benefactor = True
            self.add_message("❤️ Ты стал благотворителем! Твоя помощь сирым и убогим будет помнить вся Сибирь!")
        else:
            self.add_message("❤️ Ты уже благотворитель. Дополнительное пожертвование принято с благодарностью.")
        self.add_message(f"Пожертвовано {amount} рублей на помощь нуждающимся.")

    def get_status_text(self):
        s = self.settlement
        season_names = ["🌸 Весна", "☀️ Лето", "🍂 Осень", "❄️ Зима"]
        lines = []
        lines.append(f"Год {s.year}, сезон: {season_names[s.season]}")
        lines.append(f"Путешественников: {len(s.living_travelers())} (всего {len(s.travelers)})")
        if s.has_scurvy():
            lines.append(f"   (Цинга: {s.count_scurvy()} больных)")
        lines.append(f"Пушнина: {s.fur} | Экипировка: {s.equipment} | Деньги: {s.money} руб.")
        lines.append(f"Собаки/лошади: {s.dogs}/{s.horses} (всего {s.total_animals()})")
        lines.append(f"Открытые земли: {s.lands} | Царские грамоты: {s.charters}")
        if s.city_names:
            lines.append(f"Основанные города: {', '.join(s.city_names)} (всего {len(s.city_names)})")
        else:
            lines.append("Основанные города: нет")
        if s.church:
            lines.append("🏛️ Храм построен (порог пьянства +1000, помогает при долгах)")
        if s.palisade:
            lines.append("🛡️ Частокол построен (защита от разбойников)")
        if s.cabbage > 0:
            lines.append(f"🥬 Квашеная капуста: {s.cabbage}")
        if s.patron_of_science:
            lines.append("🔬 Меценат (поддерживает науку)")
        if s.benefactor:
            lines.append("❤️ Благотворитель (помогает сирым)")
        if s.penalty_next_season > 0:
            lines.append(f"⚠️ Штраф к добыче: -{s.penalty_next_season}%")
        if s.season == 2:
            lines.append(f"💰 Цена пушнины у купцов: {self.merchant_price} руб./ед. (можно продавать)")
        return "\n".join(lines)

# ============================ МЕНЕДЖЕР СОБЫТИЙ ============================
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
        ]
        choice = random.choice(events)
        choice()

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

# ============================ FLASK ПРИЛОЖЕНИЕ ============================
app = Flask(__name__)

# Чтение секретного ключа из переменной окружения.
# В продакшене ОБЯЗАТЕЛЬНО задайте переменную SECRET_KEY надёжной случайной строкой.
# Если ключ не задан, используется значение по умолчанию (только для разработки).
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-please-change-in-production')

# Для дополнительной безопасности можно вывести предупреждение, если ключ не переопределён.
if app.secret_key == 'dev-secret-key-please-change-in-production':
    print("⚠️ ВНИМАНИЕ: используется секретный ключ по умолчанию! Задайте переменную окружения SECRET_KEY для продакшена.")

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'game_state' not in session:
        game = Game()
        session['game_state'] = pickle.dumps(game)
    else:
        game = pickle.loads(session['game_state'])

    if request.method == 'POST':
        command = request.form.get('command', '').strip().lower()
        if command:
            game.process_command(command)
            session['game_state'] = pickle.dumps(game)

    status = game.get_status_text()
    messages = game.messages[-50:]

    return render_template('index.html', status=status, messages=messages)

@app.route('/reset')
def reset():
    session.pop('game_state', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Режим отладки включается только если переменная FLASK_DEBUG равна '1' или 'true'
    debug_mode = os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true')
    app.run(debug=debug_mode)
