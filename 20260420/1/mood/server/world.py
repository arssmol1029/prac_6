from dataclasses import dataclass

from cowsay import cowsay

from mood.common.models import MonsterParams
from mood.common.routing import RouterBatch
from mood.server.l10n import LocaleContext


class Event:
    """Базовый класс для событий на карте."""
    
    def __init__(self, *, nothing: bool = True, **kwargs):
        """
        Инициализировать событие.
        
        Args:
            nothing: Флаг, указывающий является ли событие пустым
        """
        super().__init__(**kwargs)
        self._nothing = nothing

    def __bool__(self):
        """Проверить, является ли событие непустым."""
        return not self._nothing


class EmptyEvent(Event):
    """Класс пустого события на карте."""
    
    def __init__(self):
        """Инициализировать пустое событие."""
        super().__init__(nothing=True)


class Creature:
    """Базовый класс для всех существ в мире MUD."""
    
    def __init__(
        self,
        *,
        name: str,
        pos: tuple[int, int] = (0, 0),
        damage: int = 10,
        hp: int = 100,
        **kwargs,
    ):
        """
        Инициализировать существо.
        
        Args:
            name: Имя существа
            pos: Позиция на карте
            damage: Урон существа
            hp: Здоровье существа
        """
        super().__init__(**kwargs)
        self.name = name
        self._pos = pos
        self._hp = hp
        self._damage = damage
        self._alive = True

    def take_damage(self, damage: int) -> int:
        """
        Нанести урон существу.
        
        Args:
            damage: Количество урона
            
        Returns:
            Реальный нанесенный урон
        """
        start_hp = self._hp
        if damage > self._hp:
            self._hp = 0
            self.die()
        else:
            self._hp -= damage
        return start_hp - self._hp

    def die(self) -> None:
        """Убить существо."""
        self._alive = False

    @property
    def alive(self) -> bool:
        """Проверить, живо ли существо."""
        return self._alive

    @property
    def hp(self) -> int:
        """Получить текущее здоровье существа."""
        return self._hp

    @property
    def pos(self) -> tuple[int, int]:
        """Получить текущую позицию существа."""
        return self._pos

    def move(self, *, dx: int = 0, dy: int = 0, size: int = 10) -> tuple[int, int]:
        """
        Переместить существо.
        
        Args:
            dx: Смещение по X
            dy: Смещение по Y
            size: Размер карты
            
        Returns:
            Новая позиция существа
        """
        x, y = self._pos
        x = (x + dx) % size
        y = (y + dy) % size
        self._pos = (x, y)
        return self.pos


class Monster(Event, Creature):
    """Класс монстра в мире MUD."""
    
    def __init__(self, *, params: MonsterParams, **kwargs):
        """
        Инициализировать монстра.
        
        Args:
            params: Параметры монстра
        """
        super().__init__(
            nothing=False,
            name=params.name,
            pos=params.pos,
            damage=params.damage,
            hp=params.hp,
            **kwargs,
        )
        self.hello = params.hello

    def take_damage(self, damage) -> int:
        """
        Нанести урон монстру.
        
        Args:
            damage: Количество урона
            
        Returns:
            Реальный нанесенный урон
        """
        return super().take_damage(damage)

    def die(self) -> None:
        """Убить монстра и сделать событие пустым."""
        super().die()
        self._nothing = True


@dataclass(frozen=True, slots=True)
class PlayerParams:
    """Параметры игрока."""
    
    name: str = "player"
    pos: tuple[int, int] = (0, 0)
    hp: int = 100
    damage: int = 10


class Player(Creature):
    """Класс игрока в мире MUD."""
    
    def __init__(self, *, params: PlayerParams, **kwargs):
        """
        Инициализировать игрока.
        
        Args:
            params: Параметры игрока
        """
        super().__init__(
            name=params.name,
            pos=params.pos,
            damage=params.damage,
            hp=params.hp,
            **kwargs,
        )


class MultiMUDWorld:
    """Основной класс мира MUD, управляющий игроками и монстрами."""
    
    def __init__(self, size: int = 10):
        """
        Инициализировать мир MUD.
        
        Args:
            size: Размер карты (по умолчанию 10x10)
        """
        self._size = size
        self._players: dict[str, Player] = {}
        self._dungeon: list[list[Event]] = []
        self.moving_monsters = True
        self._reset_grid()

    def _reset_grid(self) -> None:
        """Сбросить карту, заполнив её пустыми событиями."""
        self._dungeon = []
        for _ in range(self._size):
            self._dungeon.append([EmptyEvent() for _ in range(self._size)])

    @property
    def size(self) -> int:
        """Получить размер карты."""
        return self._size

    def __getitem__(self, key: tuple[int, int]) -> Event:
        """Получить событие по координатам."""
        x, y = key
        return self._dungeon[x][y]

    def __setitem__(self, key: tuple[int, int], event: Event) -> None:
        """Установить событие по координатам."""
        x, y = key
        self._dungeon[x][y] = event

    def add_player(self, username: str) -> None:
        """
        Добавить игрока в мир.
        
        Args:
            username: Имя игрока
        """
        self._players[username] = Player(params=PlayerParams(name=username))

    def remove_player(self, username: str) -> None:
        """
        Удалить игрока из мира.
        
        Args:
            username: Имя игрока
        """
        self._players.pop(username, None)

    def move_player(self, username: str, dx: int, dy: int) -> RouterBatch:
        """
        Переместить игрока.
        
        Args:
            username: Имя игрока
            dx: Смещение по X
            dy: Смещение по Y
            
        Returns:
            Список сообщений для отправки
        """
        player = self._players[username]
        x, y = player.move(dx=dx, dy=dy, size=self._size)
        out: RouterBatch = [
            (
                username,
                lambda loc, px=x, py=y: LocaleContext(loc).gettext(
                    "Moved to (%(x)d, %(y)d)"
                )
                % {"x": px, "y": py},
                None,
            )
        ]
        ev = self[x, y]
        if isinstance(ev, Monster):
            art = cowsay(message=ev.hello, cow=ev.name)
            out.append((username, art, None))
        return out

    def attack_monster(
        self,
        username: str,
        monster_name: str,
        hit_damage: int,
        weapon_name: str,
    ) -> RouterBatch:
        """
        Атаковать монстра.
        
        Args:
            username: Имя игрока
            monster_name: Имя монстра
            hit_damage: Урон атаки
            weapon_name: Название оружия
            
        Returns:
            Список сообщений для отправки
        """
        pos = self._players[username].pos
        ev = self[pos]
        if not isinstance(ev, Monster) or ev.name != monster_name:
            return [
                (
                    username,
                    lambda loc, mn=monster_name: LocaleContext(loc).gettext(
                        "No %(monster)s here"
                    )
                    % {"monster": mn},
                    None,
                )
            ]
        dealt = ev.take_damage(hit_damage)
        remaining = ev.hp
        alive = ev.alive
        if not alive:
            self[pos] = EmptyEvent()

        def broadcast(loc: str) -> str:
            ctx = LocaleContext(loc)
            dealt_hp = ctx.hp_phrase(dealt)
            weapon_disp = ctx.weapon_label(weapon_name)
            if not alive:
                return ctx.gettext(
                    "%(attacker)s attacked %(monster)s with %(weapon)s for %(dealt_hp)s and "
                    "killed the monster!"
                ) % {
                    "attacker": username,
                    "monster": monster_name,
                    "weapon": weapon_disp,
                    "dealt_hp": dealt_hp,
                }
            remaining_hp = ctx.hp_phrase(remaining)
            return ctx.gettext(
                "%(attacker)s attacked %(monster)s with %(weapon)s for %(dealt_hp)s; "
                "%(monster)s has %(remaining_hp)s left."
            ) % {
                "attacker": username,
                "monster": monster_name,
                "weapon": weapon_disp,
                "dealt_hp": dealt_hp,
                "remaining_hp": remaining_hp,
            }

        return [(None, broadcast, username)]

    def addmon(self, username: str, params: MonsterParams) -> RouterBatch:
        """
        Добавить монстра на карту.
        
        Args:
            username: Имя пользователя, добавляющего монстра
            params: Параметры монстра
            
        Returns:
            Список сообщений для отправки игрокам
        """
        x, y = params.pos
        replaced = bool(self[x, y])
        self[x, y] = Monster(params=params)

        def broadcast(loc: str) -> str:
            ctx = LocaleContext(loc)
            suffix = (
                ctx.gettext(" (replaced existing monster)") if replaced else ""
            )
            hp = ctx.hp_phrase(params.hp)
            return ctx.gettext(
                "%(user)s placed monster %(monster)s with %(hp)s at (%(x)d, %(y)d)%(suffix)s."
            ) % {
                "user": username,
                "monster": params.name,
                "hp": hp,
                "x": x,
                "y": y,
                "suffix": suffix,
            }

        return [(None, broadcast, username)]

    def get_all_monsters(self) -> list[tuple[tuple[int, int], "Monster"]]:
        """
        Получить список всех живых монстров на карте с их позициями.
        
        Returns:
            Список кортежей (позиция, монстр)
        """
        monsters = []
        for x in range(self._size):
            for y in range(self._size):
                ev = self[x, y]
                if isinstance(ev, Monster) and ev.alive:
                    monsters.append(((x, y), ev))
        return monsters

    def move_monster(self, old_pos: tuple[int, int], direction: str) -> tuple[bool, tuple[int, int], str]:
        """
        Переместить монстра в указанном направлении.
        
        Args:
            old_pos: Текущая позиция монстра
            direction: Направление движения (right/left/up/down)
            
        Returns:
            Кортеж (успех, новая_позиция, направление)
        """
        directions = {
            'right': (1, 0),
            'left': (-1, 0),
            'down': (0, 1),
            'up': (0, -1),
        }
        
        if direction not in directions:
            return False, old_pos, direction
            
        dx, dy = directions[direction]
        x, y = old_pos
        new_x = (x + dx) % self._size
        new_y = (y + dy) % self._size
        new_pos = (new_x, new_y)
        
        target_ev = self[new_pos]
        if isinstance(target_ev, Monster) and target_ev.alive:
            return False, old_pos, direction
        
        monster = self[old_pos]
        self[old_pos] = EmptyEvent()
        monster._pos = new_pos
        self[new_pos] = monster
        
        return True, new_pos, direction

    def get_players_at(self, pos: tuple[int, int]) -> list[str]:
        """
        Получить список игроков на указанной позиции.
        
        Args:
            pos: Позиция для проверки
            
        Returns:
            Список имен игроков на позиции
        """
        return [name for name, player in self._players.items() if player.pos == pos]
