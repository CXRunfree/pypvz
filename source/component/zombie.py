import pygame as pg
from .. import tool
from .. import constants as c


class Zombie(pg.sprite.Sprite):
    def __init__(self, x, y, name, head_group=None, helmetHealth=0, helmetType2Health=0, bodyHealth=c.NORMAL_HEALTH + c.LOSTHEAD_HEALTH, damage=30):
        pg.sprite.Sprite.__init__(self)

        self.name = name
        self.frames = []
        self.frame_index = 0
        self.loadImages()
        self.frame_num = len(self.frames)

        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y

        self.helmetHealth = helmetHealth
        self.helmetType2Health = helmetType2Health
        self.health = bodyHealth
        self.damage = damage
        self.dead = False
        self.lostHead = False
        self.helmet = (self.helmetHealth > 0)
        self.helmetType2 = (self.helmetType2Health > 0)
        self.head_group = head_group

        self.walk_timer = 0
        self.animate_timer = 0
        self.attack_timer = 0
        self.state = c.WALK
        self.animate_interval = 150
        self.ice_slow_ratio = 1
        self.ice_slow_timer = 0
        self.hit_timer = 0
        self.speed = 1
        self.freeze_timer = 0
        self.losthead_timer = 0
        self.is_hypno = False  # the zombie is hypo and attack other zombies when it ate a HypnoShroom

    def loadFrames(self, frames, name, image_x, colorkey=c.BLACK):
        frame_list = tool.GFX[name]
        rect = frame_list[0].get_rect()
        width, height = rect.w, rect.h
        width -= image_x

        for frame in frame_list:
            frames.append(tool.get_image(frame, image_x, 0, width, height, colorkey))

    def update(self, game_info):
        self.current_time = game_info[c.CURRENT_TIME]
        self.handleState()
        self.updateIceSlow()
        self.animation()

    def handleState(self):
        if self.state == c.WALK:
            self.walking()
        elif self.state == c.ATTACK:
            self.attacking()
        elif self.state == c.DIE:
            self.dying()
        elif self.state == c.FREEZE:
            self.freezing()

    # 濒死状态用函数
    def checkToDie(self, framesKind):
        if self.health <= 0:
            self.setDie()
        elif self.health <= c.LOSTHEAD_HEALTH:
            if not self.lostHead:
                self.changeFrames(framesKind)
                self.setLostHead()
            else:
                self.health -= (self.current_time - self.losthead_timer) / 40
                self.losthead_timer = self.current_time

    def walking(self):
        self.checkToDie(self.losthead_walk_frames)

        if self.helmetHealth <= 0 and self.helmet:
            self.changeFrames(self.walk_frames)
            self.helmet = False
        if self.helmetType2Health <= 0 and self.helmetType2:
            self.changeFrames(self.walk_frames)
            self.helmetType2 = False
            if self.name == c.NEWSPAPER_ZOMBIE:
                self.speed = 2

        if (self.current_time - self.walk_timer) > (c.ZOMBIE_WALK_INTERVAL * self.getTimeRatio()):
            self.walk_timer = self.current_time
            if self.is_hypno:
                self.rect.x += self.speed
            else:
                self.rect.x -= self.speed

    def attacking(self):
        self.checkToDie(self.losthead_attack_frames)
        
        if self.helmetHealth <= 0 and self.helmet:
            self.changeFrames(self.attack_frames)
            self.helmet = False
        if self.helmetType2Health <= 0 and self.helmetType2:
            self.changeFrames(self.attack_frames)
            self.helmetType2 = False
        if (self.current_time - self.attack_timer) > (c.ATTACK_INTERVAL * self.getTimeRatio()):
            if self.prey.health > 0:
                if self.prey_is_plant:
                    self.prey.setDamage(self.damage, self)
                else:
                    self.prey.setDamage(self.damage)
            self.attack_timer = self.current_time

        if self.prey.health <= 0:
            self.prey = None
            self.setWalk()

    def dying(self):
        pass

    def freezing(self):
        if self.old_state == c.WALK:
            self.checkToDie(self.losthead_walk_frames)
        else:
            self.checkToDie(self.losthead_attack_frames)

        if (self.current_time - self.freeze_timer) > c.FREEZE_TIME:
            self.setWalk()

    def setLostHead(self):
        self.losthead_timer = self.current_time
        self.lostHead = True
        self.animate_interval = 180
        self.speed = 0.5
        if self.head_group is not None:
            self.head_group.add(ZombieHead(self.rect.centerx, self.rect.bottom))

    def changeFrames(self, frames):
        '''change image frames and modify rect position'''
        self.frames = frames
        self.frame_num = len(self.frames)
        self.frame_index = 0

        bottom = self.rect.bottom
        centerx = self.rect.centerx
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.bottom = bottom
        self.rect.centerx = centerx

    def animation(self):
        if self.state == c.FREEZE:
            self.image.set_alpha(192)
            return

        if (self.current_time - self.animate_timer) > (self.animate_interval * self.getTimeRatio()):
            self.frame_index += 1
            if self.frame_index >= self.frame_num:
                if self.state == c.DIE:
                    self.kill()
                    return
                self.frame_index = 0
            self.animate_timer = self.current_time

        self.image = self.frames[self.frame_index]
        if self.is_hypno:
            self.image = pg.transform.flip(self.image, True, False)
        if (self.current_time - self.hit_timer) >= 200:
            self.image.set_alpha(255)
        else:
            self.image.set_alpha(192)

    def getTimeRatio(self):
        return self.ice_slow_ratio

    def setIceSlow(self):
        '''when get a ice bullet damage, slow the attack or walk speed of the zombie'''
        self.ice_slow_timer = self.current_time
        self.ice_slow_ratio = 2

    def updateIceSlow(self):
        if self.ice_slow_ratio > 1:
            if (self.current_time - self.ice_slow_timer) > c.ICE_SLOW_TIME:
                self.ice_slow_ratio = 1

    def setDamage(self, damage, ice=False, damageType=c.ZOMBIE_COMMON_DAMAGE):
        if damageType == c.ZOMBIE_DEAFULT_DAMAGE:   # 不穿透二类防具的攻击
            # 从第二类防具开始逐级传递
            if self.helmetType2:
                self.helmetType2Health -= damage
                if self.helmetType2Health <= 0:
                    self.helmetType2 = False
                    if self.helmet:
                        self.helmetHealth += self.helmetType2Health # 注意self.helmetType2Health已经带有正负
                        self.helmetType2Health = 0  # 注意合并后清零
                        if self.helmetHealth <= 0:
                            self.helmet = False
                            self.health += self.helmetHealth
                            self.helmetHealth = 0   # 注意合并后清零
                    else:
                        self.health += self.helmetType2Health
                        self.helmetType2Health = 0
            elif self.helmet:   # 不存在二类防具，但是存在一类防具
                self.helmetHealth -= damage
                if self.helmetHealth <= 0:
                    self.helmet = False
                    self.health += self.helmetHealth
                    self.helmetHealth = 0   # 注意合并后清零
            else:   # 没有防具
                self.health -= damage
        elif damageType == c.ZOMBIE_COMMON_DAMAGE:  # 无视二类防具，将攻击一类防具与本体视为整体的攻击
            if self.helmet:   # 存在一类防具
                self.helmetHealth -= damage
                if self.helmetHealth <= 0:
                    self.helmet = False
                    self.health += self.helmetHealth
                    self.helmetHealth = 0   # 注意合并后清零
            else:   # 没有一类防具
                self.health -= damage
        elif damageType == c.ZOMBIE_RANGE_DAMAGE:
            # 从第二类防具开始逐级传递
            if self.helmetType2:
                self.helmetType2Health -= damage
                if self.helmetType2Health <= 0:
                    self.helmetType2 = False
                    if self.helmet:
                        self.helmetHealth -= damage # 注意范围伤害中这里还有一个攻击
                        self.helmetHealth += self.helmetType2Health # 注意self.helmetType2Health已经带有正负
                        self.helmetType2Health = 0  # 注意合并后清零
                        if self.helmetHealth <= 0:
                            self.helmet = False
                            self.health += self.helmetHealth
                            self.helmetHealth = 0   # 注意合并后清零
                    else:
                        self.health -= damage   # 注意范围伤害中这里还有一个攻击
                        self.health += self.helmetType2Health
                        self.helmetType2Health = 0
            elif self.helmet:   # 不存在二类防具，但是存在一类防具
                self.helmetHealth -= damage
                if self.helmetHealth <= 0:
                    self.helmet = False
                    self.health += self.helmetHealth
                    self.helmetHealth = 0   # 注意合并后清零
        elif damageType == c.ZOMBIE_ASH_DAMAGE:
            self.health -= damage   # 无视任何防具
        else:
            print('警告：植物攻击类型错误，现在默认进行类豌豆射手型攻击')
            setDamage(damage, ice=ice, damageType=c.ZOMBIE_DEAFULT_DAMAGE)
        
        # 记录攻击时间              
        self.hit_timer = self.current_time
        # 冰冻减速效果
        if ice:
            self.setIceSlow()

    def setWalk(self):
        self.state = c.WALK
        self.animate_interval = 180

        if self.helmet or self.helmetType2: # 这里暂时没有考虑同时有两种防具的僵尸
            self.changeFrames(self.helmet_walk_frames)
        elif self.lostHead:
            self.changeFrames(self.losthead_walk_frames)
        else:
            self.changeFrames(self.walk_frames)

    def setAttack(self, prey, is_plant=True):
        self.prey = prey  # prey can be plant or other zombies
        self.prey_is_plant = is_plant
        self.state = c.ATTACK
        self.attack_timer = self.current_time
        self.animate_interval = 100

        if self.helmet or self.helmetType2: # 这里暂时没有考虑同时有两种防具的僵尸
            self.changeFrames(self.helmet_attack_frames)
        elif self.lostHead:
            self.changeFrames(self.losthead_attack_frames)
        else:
            self.changeFrames(self.attack_frames)

    def setDie(self):
        self.state = c.DIE
        self.animate_interval = 100
        self.changeFrames(self.die_frames)

    def setBoomDie(self):
        self.health = 0
        self.state = c.DIE
        self.animate_interval = 100
        self.changeFrames(self.boomdie_frames)

    def setFreeze(self, ice_trap_image):
        self.old_state = self.state
        self.state = c.FREEZE
        self.freeze_timer = self.current_time
        self.ice_trap_image = ice_trap_image
        self.ice_trap_rect = ice_trap_image.get_rect()
        self.ice_trap_rect.centerx = self.rect.centerx
        self.ice_trap_rect.bottom = self.rect.bottom

    def drawFreezeTrap(self, surface):
        if self.state == c.FREEZE:
            surface.blit(self.ice_trap_image, self.ice_trap_rect)

    def setHypno(self):
        self.is_hypno = True
        self.setWalk()


class ZombieHead(Zombie):
    def __init__(self, x, y):
        Zombie.__init__(self, x, y, c.ZOMBIE_HEAD, 0)
        self.state = c.DIE

    def loadImages(self):
        self.die_frames = []
        die_name = self.name
        self.loadFrames(self.die_frames, die_name, 0)
        self.frames = self.die_frames

    def setWalk(self):
        self.animate_interval = 100


class NormalZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(self, x, y, c.NORMAL_ZOMBIE, head_group)

    def loadImages(self):
        self.walk_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        walk_name = self.name
        attack_name = self.name + 'Attack'
        losthead_walk_name = self.name + 'LostHead'
        losthead_attack_name = self.name + 'LostHeadAttack'
        die_name = self.name + 'Die'
        boomdie_name = c.BOOMDIE

        frame_list = [self.walk_frames, self.attack_frames, self.losthead_walk_frames,
                      self.losthead_attack_frames, self.die_frames, self.boomdie_frames]
        name_list = [walk_name, attack_name, losthead_walk_name,
                     losthead_attack_name, die_name, boomdie_name]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name, tool.ZOMBIE_RECT[name]['x'])

        self.frames = self.walk_frames

# 路障僵尸
class ConeHeadZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(self, x, y, c.CONEHEAD_ZOMBIE, head_group, helmetHealth=c.CONEHEAD_HEALTH)

    def loadImages(self):
        self.helmet_walk_frames = []
        self.helmet_attack_frames = []
        self.walk_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        helmet_walk_name = self.name
        helmet_attack_name = self.name + 'Attack'
        walk_name = c.NORMAL_ZOMBIE
        attack_name = c.NORMAL_ZOMBIE + 'Attack'
        losthead_walk_name = c.NORMAL_ZOMBIE + 'LostHead'
        losthead_attack_name = c.NORMAL_ZOMBIE + 'LostHeadAttack'
        die_name = c.NORMAL_ZOMBIE + 'Die'
        boomdie_name = c.BOOMDIE

        frame_list = [self.helmet_walk_frames, self.helmet_attack_frames,
                      self.walk_frames, self.attack_frames, self.losthead_walk_frames,
                      self.losthead_attack_frames, self.die_frames, self.boomdie_frames]
        name_list = [helmet_walk_name, helmet_attack_name,
                     walk_name, attack_name, losthead_walk_name,
                     losthead_attack_name, die_name, boomdie_name]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name, tool.ZOMBIE_RECT[name]['x'])

        self.frames = self.helmet_walk_frames


class BucketHeadZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(self, x, y, c.BUCKETHEAD_ZOMBIE, head_group, helmetHealth=c.BUCKETHEAD_HEALTH)

    def loadImages(self):
        self.helmet_walk_frames = []
        self.helmet_attack_frames = []
        self.walk_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        helmet_walk_name = self.name
        helmet_attack_name = self.name + 'Attack'
        walk_name = c.NORMAL_ZOMBIE
        attack_name = c.NORMAL_ZOMBIE + 'Attack'
        losthead_walk_name = c.NORMAL_ZOMBIE + 'LostHead'
        losthead_attack_name = c.NORMAL_ZOMBIE + 'LostHeadAttack'
        die_name = c.NORMAL_ZOMBIE + 'Die'
        boomdie_name = c.BOOMDIE

        frame_list = [self.helmet_walk_frames, self.helmet_attack_frames,
                      self.walk_frames, self.attack_frames, self.losthead_walk_frames,
                      self.losthead_attack_frames, self.die_frames, self.boomdie_frames]
        name_list = [helmet_walk_name, helmet_attack_name,
                     walk_name, attack_name, losthead_walk_name,
                     losthead_attack_name, die_name, boomdie_name]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name, tool.ZOMBIE_RECT[name]['x'])

        self.frames = self.helmet_walk_frames


class FlagZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(self, x, y, c.FLAG_ZOMBIE, head_group, bodyHealth=c.FLAG_HEALTH + c.NORMAL_HEALTH)

    def loadImages(self):
        self.walk_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        walk_name = self.name
        attack_name = self.name + 'Attack'
        losthead_walk_name = self.name + 'LostHead'
        losthead_attack_name = self.name + 'LostHeadAttack'
        die_name = c.NORMAL_ZOMBIE + 'Die'
        boomdie_name = c.BOOMDIE

        frame_list = [self.walk_frames, self.attack_frames, self.losthead_walk_frames,
                      self.losthead_attack_frames, self.die_frames, self.boomdie_frames]
        name_list = [walk_name, attack_name, losthead_walk_name,
                     losthead_attack_name, die_name, boomdie_name]

        for i, name in enumerate(name_list):
            self.loadFrames(frame_list[i], name, tool.ZOMBIE_RECT[name]['x'])

        self.frames = self.walk_frames


class NewspaperZombie(Zombie):
    def __init__(self, x, y, head_group):
        Zombie.__init__(self, x, y, c.NEWSPAPER_ZOMBIE, head_group, helmetType2Health=c.NEWSPAPER_HEALTH)

    def loadImages(self):
        self.helmet_walk_frames = []
        self.helmet_attack_frames = []
        self.walk_frames = []
        self.attack_frames = []
        self.losthead_walk_frames = []
        self.losthead_attack_frames = []
        self.die_frames = []
        self.boomdie_frames = []

        helmet_walk_name = self.name
        helmet_attack_name = self.name + 'Attack'
        walk_name = self.name + 'NoPaper'
        attack_name = self.name + 'NoPaperAttack'
        losthead_walk_name = self.name + 'LostHead'
        losthead_attack_name = self.name + 'LostHeadAttack'
        die_name = self.name + 'Die'
        boomdie_name = c.BOOMDIE

        frame_list = [self.helmet_walk_frames, self.helmet_attack_frames,
                      self.walk_frames, self.attack_frames, self.losthead_walk_frames,
                      self.losthead_attack_frames, self.die_frames, self.boomdie_frames]
        name_list = [helmet_walk_name, helmet_attack_name,
                     walk_name, attack_name, losthead_walk_name,
                     losthead_attack_name, die_name, boomdie_name]

        for i, name in enumerate(name_list):
            if name == c.BOOMDIE:
                color = c.BLACK
            else:
                color = c.WHITE
            self.loadFrames(frame_list[i], name, tool.ZOMBIE_RECT[name]['x'], color)

        self.frames = self.helmet_walk_frames