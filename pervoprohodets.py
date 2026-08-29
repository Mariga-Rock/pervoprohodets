import random
import sys

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
        self.patron_of_science = False   # меценат
        self.benefactor = False          # благотворитель

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
        self.commands = {
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

    def synergy_multiplier(self, count):
        if count <= 0:
            return 0
        if count == 1:
            return 1.0
        if count == 2:
            return 2.5
        if count == 3:
            return 7.5
        return 7.5 * (1.3 ** (count - 3))

    def run(self):
        print("="*70)
        print("Добро пожаловать в игру «Первопроходец Сибири»!")
        print()
        print("Ты — первопроходец, отважный землепроходец, волею судьбы оказавшийся")
        print("на пороге неизведанных сибирских земель. Твоя задача — выжить в суровой")
        print("тайге, добыть пушнину, наладить торговлю с купцами и заслужить царскую")
        print("милость.")
        print()
        print("Цель игры:")
        print("  • Накопи 5 грамот — и ты сможешь либо основать город (списав 5 грамот),")
        print("    либо получить двух новых путешественников. Города можно основывать")
        print("    и дальше: для второго нужно 10 грамот, для третьего — 15 и так далее.")
        print("  • Накопи 100 грамот — стань великим князем Сибири, и город будет")
        print("    назван в твою честь (великая победа).")
        print()
        print("Царские грамоты можно получить только через отправку пушнины в казну (100 единиц пушнины = 1 грамота).")
        print()
        print("Важно: Накопленные деньги нужно вкладывать в дело — покупать экипировку,")
        print("заводить собак и лошадей или строить храмы. Если деньги лежат мёртвым грузом")
        print("и их становится больше 2000 рублей (или 3000, если построен храм),")
        print("дальнейшие исследования буксуют, а в вашем стане начинают процветать")
        print("пьянство и разгул — это отнимает царские грамоты и снижает добычу пушнины.")
        print("Вкладывайте в дело, чтобы держать ситуацию под контролем!")
        print()
        print("Сезоны года:")
        print("  🌸 Весна — время подготовки к новому сезону. Можно закупать экипировку и животных.")
        print("  ☀️ Лето — основное время для экспедиций. Отправляй путешественников в")
        print("       новые земли или в уже открытые регионы, чтобы добыть пушнину.")
        print("       С приходом лета все больные цингой излечиваются!")
        print("  🍂 Осень — завершение охоты, подсчёт добычи. Также только осенью можно")
        print("       продавать пушнину купцам и покупать квашеную капусту. Возможны набеги")
        print("       разбойников, так что будь начеку.")
        print("  ❄️ Зима — дальние походы невозможны. Тратится экипировка и пушнина на")
        print("       отопление и пропитание. Если запасы на исходе — люди гибнут, но только")
        print("       если у тебя нет достаточно квашеной капусты (1 капуста на каждого путешественника).")
        print("       Капуста спасает от голода!")
        print()
        print("Каждый ход, если есть больные цингой и есть капуста, 1 капуста лечит 1 больного.")
        print()
        print("Открытие новых земель требует дополнительных затрат экипировки (5 единиц).")
        print()
        print("Ты можешь пожертвовать деньги на науку (200 руб) и получить статус мецената,")
        print("или на помощь сирым и убогим (150 руб) и стать благотворителем.")
        print()
        print("Исследуй новые земли, отражай набеги разбойников, заботься о своих людях.")
        print("В путь!")
        print("="*70)
        print("Введите 'помощь' для списка команд.")
        print()

        while self.running:
            self.display_status()
            if not self.check_game_over():
                break
            cmd = input("> ").strip().lower()
            if not cmd:
                continue

            matched_cmd = None
            args = []
            for command in sorted(self.commands.keys(), key=len, reverse=True):
                if cmd == command or cmd.startswith(command + ' '):
                    matched_cmd = command
                    args = cmd[len(command):].strip().split()
                    break

            if matched_cmd:
                try:
                    self.commands[matched_cmd](args)
                except Exception as e:
                    print("Ошибка выполнения команды:", e)
            else:
                print("Неизвестная команда. Введите 'помощь' для списка.")

            if not self.running:
                break
            self.after_action()

    def after_action(self):
        self.check_debt()
        self.heal_scurvy_with_cabbage()
        s = self.settlement
        if s.charters >= 5:
            current_level = s.charters // 5
            if current_level > s.last_offer_level:
                self.offer_charter_choice()

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
                print(f"🥬 {t.name} вылечен от цинги квашеной капустой.")
            else:
                break
        if healed > 0 and s.has_scurvy():
            print("⚠️ Не хватило капусты, некоторые путешественники всё ещё больны.")
        elif healed > 0:
            print("💚 Все больные цингой вылечены!")

    def offer_charter_choice(self):
        s = self.settlement
        current_level = s.charters // 5
        print(f"\n🌟 Ты достиг {s.charters} царских грамот! Теперь у тебя есть выбор:")
        print("  1 - Основать город (потратить 5 грамот) — город будет назван твоим именем.")
        print("  2 - Получить двух новых путешественников в отряд (грамоты останутся).")
        choice = input("Твой выбор (1 или 2): ").strip()
        if choice == "1":
            if s.charters >= 5:
                s.charters -= 5
                city_name = input("Введите название города: ").strip()
                if city_name == "":
                    city_name = "Безымянный"
                s.city_names.append(city_name)
                print(f"🏙️ Город {city_name} основан! Всего городов: {len(s.city_names)}.")
                s.last_offer_level = current_level
            else:
                print("❌ Что-то пошло не так: грамот недостаточно.")
        elif choice == "2":
            names = ["Семён", "Демид", "Артемий", "Прокопий", "Гаврила"]
            for _ in range(2):
                name = random.choice(names) + " (новый)"
                new_t = Traveler(name)
                s.travelers.append(new_t)
            print("👥 Два новых путешественника присоединились к твоему отряду! Теперь у тебя {} человек.".format(len(s.living_travelers())))
            s.last_offer_level = current_level
        else:
            print("❌ Неверный ввод. Попробуй ещё раз.")
            self.offer_charter_choice()

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
                print(f"☀️ С приходом лета все {healed_count} путешественников излечились от цинги!")
            else:
                print("☀️ Наступило лето. Все здоровы.")

        if s.season == 0:
            s.year += 1
            self.merchant_price = random.randint(2, 10)
            print(f"🎉 Поздравляем! Ты занимаешься освоением Сибири в течение уже {s.year} лет. За это время тебе на самом высочайшем уровне пожаловали {s.total_charters_earned} грамот.")

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
                print(f"❄️ Зимой потрачено {cabbage_spent} квашеной капусты на пропитание (осталось: {s.cabbage})")
        else:
            cabbage_spent = 0
            print("🥬 Капусты нет – зимний расход пропущен.")

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
                print(f"❄️ Зимний голод! Умерло {deaths} путешественников.")
            else:
                print("❄️ Зимой ресурсов не хватило, но голод не привёл к смертям.")
        elif had_enough_cabbage:
            if deficit_equip > 0 or deficit_fur > 0:
                print("🥬 Благодаря квашеной капусте зимний голод не унёс ни одной жизни!")
        else:
            print("❄️ Зима прошла благополучно, ресурсов хватило.")

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
                print(f"🍺 Пьянство и разгул! Царь отнял 1 грамоту. Осталось грамот: {s.charters}")
            else:
                s.penalty_next_season += 30
                print("🍺 Пьянство и лень! Путешественники будут добывать меньше пушнины в следующем сезоне.")
                s.money = threshold

    def check_game_over(self):
        s = self.settlement
        if len(s.living_travelers()) == 0:
            print("💀 Все путешественники погибли. Игра окончена.")
            self.running = False
            return False
        if s.fur <= 0 and s.equipment <= 0 and s.season == 3:
            print("💀 Зимой одновременно закончились пушнина и экипировка – нечем кормить и греть людей. Все погибли от голода и холода. Игра окончена.")
            self.running = False
            return False
        if s.charters >= 100:
            print("🏙️ ВЕЛИКАЯ ПОБЕДА! Ты накопил 100 грамот, стал великим князем Сибири, и город назван в твою честь! Ты вошёл в историю как величайший первопроходец!")
            self.running = False
            return False
        return True

    def check_debt(self):
        s = self.settlement
        if s.money <= -20:
            print("\n⚠️ Твои долги достигли критической отметки (-20 рублей)! Нужно срочно найти деньги.")
            options = []
            if s.dogs > 0:
                options.append("1 - Продать собаку (30 руб)")
            if s.horses > 0:
                options.append("2 - Продать лошадь (50 руб)")
            if s.church:
                options.append("3 - Обратиться в храм за помощью (случайно)")
            if not options:
                print("💀 У тебя нет никаких активов, чтобы расплатиться. Игра окончена.")
                self.running = False
                return
            print("Выбери действие:")
            for opt in options:
                print("  " + opt)
            choice = input("> ").strip()
            if choice == "1" and s.dogs > 0:
                s.dogs -= 1
                s.money += 30
                print("🐕 Ты продал собаку за 30 рублей. Долг погашен.")
            elif choice == "2" and s.horses > 0:
                s.horses -= 1
                s.money += 50
                print("🐎 Ты продал лошадь за 50 рублей. Долг погашен.")
            elif choice == "3" and s.church:
                if random.random() < 0.5:
                    donation = random.randint(30, 60)
                    s.money += donation
                    print(f"🙏 Храм помог тебе! Ты получил {donation} рублей.")
                else:
                    print("🙏 Храм не смог помочь, но ты можешь попробовать ещё раз позже.")
            else:
                print("❌ Неверный выбор. Попробуй ещё раз.")
                self.check_debt()

    def display_status(self):
        s = self.settlement
        season_names = ["Весна", "Лето", "Осень", "Зима"]
        print("\n" + "-"*50)
        print(f"Год {s.year}, сезон: {season_names[s.season]}")
        print(f"Путешественников: {len(s.living_travelers())} (всего {len(s.travelers)})")
        if s.has_scurvy():
            print(f"   (Цинга: {s.count_scurvy()} больных)")
        print(f"Пушнина: {s.fur} | Экипировка: {s.equipment} | Деньги: {s.money} руб.")
        print(f"Собаки/лошади: {s.dogs}/{s.horses} (всего {s.total_animals()})")
        print(f"Открытые земли: {s.lands} | Царские грамоты: {s.charters}")
        if s.city_names:
            print(f"Основанные города: {', '.join(s.city_names)} (всего {len(s.city_names)})")
        else:
            print("Основанные города: нет")
        if s.church:
            print("🏛️ Храм построен (порог пьянства +1000, помогает при долгах)")
        if s.palisade:
            print("🛡️ Частокол построен (защита от разбойников)")
        if s.cabbage > 0:
            print(f"🥬 Квашеная капуста: {s.cabbage}")
        if s.patron_of_science:
            print("🔬 Меценат (поддерживает науку)")
        if s.benefactor:
            print("❤️ Благотворитель (помогает сирым)")
        if s.penalty_next_season > 0:
            print(f"⚠️ Штраф к добыче: -{s.penalty_next_season}%")
        if s.season == 2:
            print(f"💰 Цена пушнины у купцов: {self.merchant_price} руб./ед. (можно продавать)")
        print("-"*50)

    def cmd_help(self, args):
        print("""
Доступные команды:
  отправить <кол-во> <регион>          - отправить экспедицию (только летом). Регион: 'новый' или номер открытой земли (1..lands).
                                           При нападении разбойников предложат выбор: биться или откупиться.
                                           Открытие новых земель требует 5 дополнительных единиц экипировки.
  продать пушнину <кол-во>             - продать пушнину купцам (ТОЛЬКО ОСЕНЬЮ).
  послать пушнину в царскую казну <кол-во> - обменять пушнину на грамоты (100 за 1 грамоту) в любое время.
  купить экипировку <кол-во>           - купить экипировку (цена 5 руб/ед) в любое время.
  купить собаку [кол-во]               - купить собак (50 руб/шт), по умолчанию 1.
  купить лошадь [кол-во]               - купить лошадей (50 руб/шт), по умолчанию 1.
  купить капусту <кол-во>              - купить квашеную капусту (10 руб/ед) ТОЛЬКО ОСЕНЬЮ.
                                           При покупке сразу лечит цингу (1 ед. = 1 больной).
  построить храм                       - построить храм (500 руб, повышает порог пьянства до 3000, помогает при долгах).
  построить частокол                   - построить частокол (100 руб, защита от разбойников).
  подкупить разбойников <сумма>        - откупиться от разбойников на сезон (сумма).
  отправить семье <сумма>              - отправить деньги семье (любая сумма). Семья поблагодарит.
  основать город                       - основать город, если есть достаточно грамот (5 + 5*число_уже_основанных_городов).
                                           При вводе команды будет запрошено название города.
  пожертвовать науке <сумма>           - пожертвовать на развитие науки (≥200 руб) – получить статус мецената.
  пожертвовать сирым <сумма>           - пожертвовать на помощь сирым и убогим (≥150 руб) – получить статус благотворителя.
  статус                               - показать текущее состояние.
  следующий сезон                      - перейти к следующему сезону.
  пропустить год                       - пропустить целый год (перейти к весне). Стоимость: 50 руб. и 2 капусты (если есть). Снижает выносливость путешественников.
  помощь                               - показать это сообщение.
  выход                                - выйти из игры.

Сезоны года:
  🌸 Весна — время подготовки к новому сезону. Можно закупать экипировку и животных.
  ☀️ Лето — основное время для экспедиций. Отправляй путешественников в
       новые земли или в уже открытые регионы, чтобы добыть пушнину.
       С приходом лета все больные цингой излечиваются!
  🍂 Осень — завершение охоты, подсчёт добычи. Также только осенью можно
       продавать пушнину купцам и покупать квашеную капусту. Возможны набеги
       разбойников, так что будь начеку.
  ❄️ Зима — дальние походы невозможны. Тратится экипировка и пушнина на
       отопление и пропитание. Если запасы на исходе — люди гибнут, но только
       если у тебя нет достаточно квашеной капусты (1 капуста на каждого путешественника).
       Капуста спасает от голода!

Каждый ход, если есть больные цингой и есть капуста, 1 капуста лечит 1 больного.
Царские грамоты можно получить только через отправку пушнины в казну (100 единиц пушнины = 1 грамота).

Важно: Если денег становится больше 2000 рублей (или 3000 при наличии храма),
начинаются пьянство и разгул – это отнимает грамоты и снижает добычу.
Открытие новых земель требует дополнительных 5 единиц экипировки.
Пожертвования на науку (≥200 руб) дают статус мецената, на сирых (≥150 руб) – статус благотворителя.
""")

    def cmd_quit(self, args):
        print("Выход из игры.")
        self.running = False

    def cmd_status(self, args):
        self.display_status()

    def cmd_skip(self, args):
        self.advance_season()
        if self.running:
            self.check_game_over()

    def cmd_skip_year(self, args):
        s = self.settlement
        if s.money < 50:
            print("❌ Недостаточно денег для пропуска года (нужно 50 руб.).")
            return

        s.money -= 50

        if s.cabbage > 0:
            spent_cabbage = min(2, s.cabbage)
            s.cabbage -= spent_cabbage
            print(f"🥬 Потрачено {spent_cabbage} квашеной капусты.")
        else:
            print("🥬 Капусты не было – пропускаем без неё.")

        for t in s.living_travelers():
            t.endurance = max(1, t.endurance - 1)

        s.penalty_next_season = 0

        s.year += 1
        s.season = 0
        self.merchant_price = random.randint(2, 10)

        print(f"⏩ Ты пропустил целый год! Теперь год {s.year}, сезон Весна.")
        print(f"🎉 Поздравляем! Ты занимаешься освоением Сибири в течение уже {s.year} лет. За это время тебе на самом высочайшем уровне пожаловали {s.total_charters_earned} грамот.")
        if self.running:
            self.check_game_over()

    def cmd_sell(self, args):
        if self.settlement.season != 2:
            print("❌ Продавать пушнину можно только осенью!")
            return
        if not args:
            print("Укажите количество пушнины для продажи.")
            return
        try:
            amount = int(args[0])
        except:
            print("Неверное число.")
            return
        s = self.settlement
        if amount <= 0:
            print("Количество должно быть положительным.")
            return
        if amount > s.fur:
            print(f"У вас только {s.fur} пушнины.")
            return
        s.fur -= amount
        revenue = amount * self.merchant_price
        bonus = 1 + 0.1 * s.charters
        revenue = int(revenue * bonus)
        s.money += revenue
        print(f"✅ Продано {amount} пушнины за {revenue} рублей.")

    def cmd_give_to_tsar(self, args):
        if not args:
            print("Укажите количество пушнины для отправки в царскую казну.")
            return
        try:
            amount = int(args[0])
        except:
            print("Неверное число.")
            return
        s = self.settlement
        if amount <= 0:
            print("Количество должно быть положительным.")
            return
        if amount > s.fur:
            print(f"У вас только {s.fur} пушнины.")
            return
        earned = amount // 100
        if earned == 0:
            print("Нужно как минимум 100 пушнины для получения грамоты.")
            return
        s.fur -= amount
        s.charters += earned
        s.total_charters_earned += earned
        s.total_fur_sent_to_tsar += amount
        print(f"👑 Отправлено {amount} пушнины в царскую казну. Царь пожаловал тебе {earned} грамот! Это высочайшая царская милость! Всего грамот: {s.charters}.")

    def cmd_expedition(self, args):
        if self.settlement.season != 1:
            print("❌ Экспедиции возможны только летом!")
            return
        if len(args) < 2:
            print("Использование: отправить <кол-во путешественников> <регион>")
            print("Регион: 'новый' или число от 1 до", self.settlement.lands)
            return
        try:
            count = int(args[0])
        except:
            print("Неверное число.")
            return
        region = args[1]
        s = self.settlement
        living = s.living_travelers()
        if count > len(living):
            print(f"У вас только {len(living)} живых путешественников.")
            return
        if count <= 0:
            print("Нужно отправить хотя бы одного.")
            return

        is_new = (region == 'новый')
        extra_equip_cost = 5 if is_new else 0
        need_equip = count * 3 + extra_equip_cost

        if s.equipment < need_equip:
            print(f"Недостаточно экипировки. Нужно {need_equip}, есть {s.equipment}.")
            return

        if is_new:
            region_idx = s.lands + 1
        else:
            try:
                region_idx = int(region)
            except:
                print("Регион должен быть 'новый' или число.")
                return
            if region_idx < 1 or region_idx > s.lands:
                print(f"Доступны регионы от 1 до {s.lands} или 'новый'.")
                return

        s.equipment -= need_equip
        if is_new:
            print(f"🗺️ Открыта новая земля! Потрачено 5 дополнительных единиц экипировки.")
            s.lands += 1
            print(f"Теперь открытых земель: {s.lands}")

        total_hunting = sum(t.hunting for t in living[:count])
        synergy = self.synergy_multiplier(count)
        base_fur = total_hunting * 2 * synergy
        land_bonus = 1 + 0.1 * s.lands
        penalty = 1 - s.penalty_next_season / 100.0
        if penalty < 0:
            penalty = 0
        animal_bonus = 1 + 0.05 * s.total_animals()
        random_factor = random.uniform(0.8, 1.2)
        fur_gained = int(base_fur * land_bonus * animal_bonus * penalty * random_factor)
        if fur_gained < 0:
            fur_gained = 0

        # Болезни цингой в экспедиции НЕТ (летом нельзя заболеть)

        bandit_chance = 0.2 if not s.palisade else 0.1
        if random.random() < bandit_chance:
            print("\n🏴 ВНИМАНИЕ! На ваш отряд напали разбойники!")
            print("Что будешь делать?")
            print("  1 - Вступить в бой (риск потери выносливости, животных, пушнины и даже людей)")
            print("  2 - Откупиться (заплатить деньги, разбойники уйдут)")
            fight = False
            while True:
                choice = input("Твой выбор (1 или 2): ").strip()
                if choice == "2":
                    ransom = random.randint(30, 100)
                    if s.money >= ransom:
                        s.money -= ransom
                        print(f"💰 Ты заплатил {ransom} рублей. Разбойники приняли плату и ушли.")
                        fight = False
                        break
                    else:
                        print(f"😤 У тебя всего {s.money} рублей, а нужно {ransom}. Денег не хватает – придётся драться!")
                        fight = True
                        break
                elif choice == "1":
                    fight = True
                    break
                else:
                    print("❌ Неверный ввод. Попробуй ещё раз.")

            if fight:
                print("⚔️ Ты вступаешь в бой с разбойниками!")
                killed_in_battle = 0
                stolen = 0
                for t in living[:count]:
                    loss = random.randint(1, 2)
                    t.endurance = max(1, t.endurance - loss)
                print("💪 Путешественники потеряли часть выносливости в бою.")
                if s.dogs > 0 or s.horses > 0:
                    if random.random() < 0.3:
                        if s.horses > 0:
                            s.horses -= 1
                            print("🐎 Разбойники убили одну лошадь.")
                        elif s.dogs > 0:
                            s.dogs -= 1
                            print("🐕 Разбойники убили одну собаку.")
                if random.random() < 0.2:
                    stolen = fur_gained // 3
                    if stolen > 0:
                        fur_gained -= stolen
                        print(f"🏴 Разбойники украли {stolen} пушнины.")
                if random.random() < 0.1:
                    victims = random.sample(living[:count], min(1, count))
                    for v in victims:
                        v.alive = False
                    killed_in_battle = len(victims)
                    print(f"⚔️ Разбойники убили {killed_in_battle} путешественника(ов).")
                    s.remove_dead()
                print("✅ Бой окончен. Отряд продолжает путь.")
                if killed_in_battle == 0 and stolen == 0:
                    print("Разбойники ушли ни с чем.")
                elif killed_in_battle > 0:
                    if killed_in_battle == 1:
                        print("⚔️ В бою погиб 1 путешественник.")
                    else:
                        print(f"⚔️ В бою погибло {killed_in_battle} путешественников.")
        else:
            print("✅ Поход прошёл без нападений.")

        s.fur += fur_gained
        print(f"🦊 Добыто {fur_gained} пушнины.")
        s.penalty_next_season = 0

    def cmd_buy_equipment(self, args):
        if not args:
            print("Укажите количество экипировки для покупки.")
            return
        try:
            amount = int(args[0])
        except:
            print("Неверное число.")
            return
        s = self.settlement
        cost = amount * 5
        if cost > s.money:
            print(f"Недостаточно денег. Нужно {cost}, есть {s.money}.")
            return
        s.money -= cost
        s.equipment += amount
        print(f"✅ Куплено {amount} экипировки. Осталось денег: {s.money}.")

    def cmd_buy_dog(self, args):
        s = self.settlement
        if args and args[0].isdigit():
            count = int(args[0])
        else:
            count = 1
        if count <= 0:
            print("Количество должно быть положительным.")
            return
        total_cost = count * 50
        if s.money < total_cost:
            print(f"Недостаточно денег. Нужно {total_cost} руб., есть {s.money}.")
            return
        s.money -= total_cost
        s.dogs += count
        print(f"🐕 Куплено {count} собак. Всего собак: {s.dogs}")

    def cmd_buy_horse(self, args):
        s = self.settlement
        if args and args[0].isdigit():
            count = int(args[0])
        else:
            count = 1
        if count <= 0:
            print("Количество должно быть положительным.")
            return
        total_cost = count * 50
        if s.money < total_cost:
            print(f"Недостаточно денег. Нужно {total_cost} руб., есть {s.money}.")
            return
        s.money -= total_cost
        s.horses += count
        print(f"🐎 Куплено {count} лошадей. Всего лошадей: {s.horses}")

    def cmd_buy_cabbage(self, args):
        if self.settlement.season != 2:
            print("❌ Квашеную капусту можно покупать только осенью!")
            return
        if not args:
            print("Укажите количество капусты.")
            return
        try:
            amount = int(args[0])
        except:
            print("Неверное число.")
            return
        s = self.settlement
        if amount <= 0:
            print("Количество должно быть положительным.")
            return
        cost = amount * 10
        if cost > s.money:
            print(f"Недостаточно денег. Нужно {cost}, есть {s.money}.")
            return
        s.money -= cost
        sick = [t for t in s.living_travelers() if t.scurvy]
        healed = min(len(sick), amount)
        for i in range(healed):
            sick[i].scurvy = False
        remaining = amount - healed
        s.cabbage += remaining
        print(f"🥬 Куплено {amount} квашеной капусты. Из них {healed} использовано на лечение цинги, {remaining} добавлено в запас.")
        if healed > 0:
            print(f"💚 Вылечено {healed} путешественников от цинги.")
        if s.cabbage == 0:
            print("Вся капуста ушла на лечение, запаса не осталось.")
        else:
            print(f"Теперь в запасе {s.cabbage} капусты.")

    def cmd_build_church(self, args):
        s = self.settlement
        if s.church:
            print("Храм уже построен.")
            return
        if s.money < 500:
            print("Недостаточно денег. Нужно 500 руб.")
            return
        s.money -= 500
        s.church = True
        print("🏛️ Храм построен! Теперь порог пьянства повышен до 3000 рублей, и при долгах можно обратиться за помощью.")

    def cmd_build_palisade(self, args):
        s = self.settlement
        if s.palisade:
            print("Частокол уже построен.")
            return
        if s.money < 100:
            print("Недостаточно денег. Нужно 100 руб.")
            return
        s.money -= 100
        s.palisade = True
        print("🛡️ Частокол построен! Риск нападений разбойников снижен.")

    def cmd_bribe_bandits(self, args):
        if not args:
            print("Укажите сумму для подкупа.")
            return
        try:
            amount = int(args[0])
        except:
            print("Неверное число.")
            return
        s = self.settlement
        if amount > s.money:
            print("Недостаточно денег.")
            return
        s.money -= amount
        self.bandit_activity = max(0.05, self.bandit_activity - 0.1)
        print(f"🤝 Разбойники подкуплены на {amount} руб. Активность снижена.")

    def cmd_send_money_to_family(self, args):
        if not args:
            print("Укажите сумму для отправки семье.")
            return
        try:
            amount = int(args[0])
        except:
            print("Неверное число.")
            return
        s = self.settlement
        if amount <= 0:
            print("Сумма должна быть положительной.")
            return
        if amount > s.money:
            print(f"У вас только {s.money} рублей. Не хватает.")
            return
        s.money -= amount
        print(f"📨 Ты отправил {amount} рублей своей семье. Семья передаёт спасибо и очень гордится твоими успехами! ❤️")

    def cmd_found_city(self, args):
        s = self.settlement
        required = 5 + len(s.city_names) * 5
        if s.charters >= required:
            s.charters -= required
            city_name = input("Введите название города: ").strip()
            if city_name == "":
                city_name = "Безымянный"
            s.city_names.append(city_name)
            print(f"🏙️ Город {city_name} основан! Всего городов: {len(s.city_names)}. Потрачено {required} грамот.")
        else:
            print(f"❌ Для основания следующего города нужно {required} грамот, а у тебя только {s.charters}.")

    def cmd_donate_science(self, args):
        if not args:
            print("Укажите сумму для пожертвования на науку.")
            return
        try:
            amount = int(args[0])
        except:
            print("Неверное число.")
            return
        s = self.settlement
        if amount <= 0:
            print("Сумма должна быть положительной.")
            return
        if amount > s.money:
            print(f"У вас только {s.money} рублей. Не хватает.")
            return
        if amount < 200:
            print("Минимальное пожертвование на науку – 200 рублей.")
            return
        s.money -= amount
        if not s.patron_of_science:
            s.patron_of_science = True
            print("🔬 Ты стал меценатом! Наука в Сибири получит развитие. Спасибо за твой вклад!")
        else:
            print("🔬 Ты уже меценат. Но дополнительное пожертвование принято с благодарностью.")
        print(f"Пожертвовано {amount} рублей на развитие науки.")

    def cmd_donate_charity(self, args):
        if not args:
            print("Укажите сумму для пожертвования на помощь сирым.")
            return
        try:
            amount = int(args[0])
        except:
            print("Неверное число.")
            return
        s = self.settlement
        if amount <= 0:
            print("Сумма должна быть положительной.")
            return
        if amount > s.money:
            print(f"У вас только {s.money} рублей. Не хватает.")
            return
        if amount < 150:
            print("Минимальное пожертвование на помощь сирым – 150 рублей.")
            return
        s.money -= amount
        if not s.benefactor:
            s.benefactor = True
            print("❤️ Ты стал благотворителем! Твоя помощь сирым и убогим будет помнить вся Сибирь!")
        else:
            print("❤️ Ты уже благотворитель. Дополнительное пожертвование принято с благодарностью.")
        print(f"Пожертвовано {amount} рублей на помощь нуждающимся.")

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
        print(f"🎉 Случайная находка: обнаружено богатое соболиное гнездо! +{bonus} пушнины.")

    def event_find_equipment(self):
        bonus = random.randint(5, 20)
        self.game.settlement.equipment += bonus
        print(f"🎉 Найдена старая кладовая! +{bonus} экипировки.")

    def event_merchant_cheat(self):
        if self.game.settlement.money > 20:
            loss = random.randint(10, 50)
            self.game.settlement.money -= loss
            print(f"😤 Купец обвесил вас! Потеряно {loss} рублей.")
        else:
            print("Купец попытался обмануть, но у вас слишком мало денег – он ушёл ни с чем.")

    def event_blizzard(self):
        if self.game.settlement.season == 3:
            loss = random.randint(5, 15)
            self.game.settlement.equipment = max(0, self.game.settlement.equipment - loss)
            print(f"❄️ Снежная буря! Потеряно {loss} экипировки.")

    def event_animal_rampage(self):
        s = self.game.settlement
        if s.total_animals() > 0:
            loss = random.randint(1, min(3, s.total_animals()))
            for _ in range(loss):
                if s.dogs > 0:
                    s.dogs -= 1
                elif s.horses > 0:
                    s.horses -= 1
            print(f"🐾 Животные взбесились! Потеряно {loss} голов скота.")

if __name__ == "__main__":
    game = Game()
    game.run()
    print("Спасибо за игру! До новых встреч.")
