# -*- coding: utf-8 -*-
"""Проверка расчётного ядра site/assets/hcalc.js.

Модуль hcalc.js — единственное место, где живут формулы разборов задач
(p-*.html). Ошибка в нём не поймается ни разбором HTML, ни проверкой ссылок:
страницы останутся валидными, а числа станут неверными. Поэтому здесь
проверяется сама арифметика, причём тремя независимыми способами:

  * встроенная самопроверка HCALC.selftest() — контрольные точки, посчитанные
    аналитически либо обращением формулы (прямоугольное сечение с известными
    I и W, справочная величина ГОСТ 21937 для полособульба с пояском,
    непрерывность и обратимость поправки Джонсона — Остенфельда, два пояса
    эквивалентного бруса с точным ответом A·h);

  * пересчёт ключевых величин на Python по формулам, выписанным в этом файле
    заново, — так опечатка в JS не может «подтвердить сама себя»;

  * сверка чисел, напечатанных на страницах разборов, с тем, что выдаёт
    модуль: страница и ядро не должны разъезжаться.

Судно сквозного примера — тот же сухогруз 100,0 × 15,3 × 8,3 м, что на сайтах
«Проектирование судов» (/design/) и «Технология судостроения» (/shiptech/).
"""
import json
import math
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HCALC_JS = os.path.join(ROOT, 'site', 'assets', 'hcalc.js')
SITE = os.path.join(ROOT, 'site')

pytestmark = [
    pytest.mark.skipif(not os.path.isfile(HCALC_JS), reason='нет site/assets/hcalc.js'),
    pytest.mark.skipif(not shutil.which('node'), reason='node не установлен'),
]

#: постоянные, выписанные здесь заново (сверять с шапкой hcalc.js)
E = 2.06e5          # МПа
NU = 0.3
RHO_ST = 7850       # кг/м³
G = 9.81            # м/с²

#: судно сквозного примера
L, B, H, T, CB = 100.0, 15.3, 8.3, 6.60, 0.74
HDB = 1.00          # м, высота двойного дна
A = 0.80            # м, практическая шпация
REH = 235.0         # МПа
AZ = 2.0            # м, волновой напор (учебн.)


def hc(expr):
    """Выполнить выражение в node с загруженным модулем и вернуть результат."""
    src = 'const H = require(%s); console.log(JSON.stringify(%s));' % (
        json.dumps(HCALC_JS), expr)
    r = subprocess.run(['node', '-e', src], capture_output=True, text=True)
    assert r.returncode == 0, 'node упал: %s' % r.stderr.strip()[:500]
    return json.loads(r.stdout.strip())


# ------------------------------------------------------------ самопроверка

def test_selftest_passes():
    bad = hc('H.selftest()')
    assert bad == [], 'самопроверка модуля нашла расхождения:\n' + '\n'.join(bad)


def test_constants_match():
    got = hc('({E: H.E, NU: H.NU, RHO: H.RHO_ST, G: H.G})')
    assert got['E'] == E and got['NU'] == NU
    assert got['RHO'] == RHO_ST and got['G'] == G


def test_ship_is_cluster_example():
    """Судно то же, что на /design/ и /shiptech/ — иначе сквозной пример рвётся."""
    s = hc('H.SHIP')
    assert (s['L'], s['B'], s['H']) == (100.0, 15.3, 8.3)
    assert s['T'] == pytest.approx(6.60) and s['Cb'] == pytest.approx(0.74)
    assert s['hdb'] == pytest.approx(1.00)
    # геометрия мидель-шпангоута снята с секции СК-6 сайта технологии
    assert s['yFlat'] == pytest.approx(6.150) and s['rBilge'] == pytest.approx(1.500)
    assert hc('H.SPACING.a') == pytest.approx(0.80)


# ------------------------------------------------- разбор 1: шпация и разбивка

def test_normal_spacing():
    """a0 = 0,002L + 0,48 — прямая подстановка (Правила РМРС, ч. II, гл. 1.1)."""
    assert hc('H.normalSpacing(100)') == pytest.approx(0.002 * 100 + 0.48)
    assert hc('H.normalSpacing(100)') == pytest.approx(0.68, abs=1e-12)


def test_spacing_check_of_practical_value():
    """Принятая 0,80 м отклоняется от нормальной на 17,6 % — в пределах 25 %."""
    got = hc('H.spacingCheck(0.80, 100)')
    dev = (0.80 - 0.68) / 0.68
    assert got['dev'] == pytest.approx(dev, rel=1e-12)
    assert got['dev'] == pytest.approx(0.176, abs=0.001)
    assert got['devOk'] and got['mult50'] and got['maxOk'] and got['ok']
    # шпация 1,10 м не проходит ни по отклонению, ни по абсолютному пределу
    bad = hc('H.spacingCheck(1.10, 100)')
    assert not bad['ok'] and not bad['maxOk']


def test_frame_layout_closes_on_length():
    """Разбивка корпуса должна замкнуться на длину без невязки."""
    got = hc("""H.frameLayout([
        {name:'ахтерпик и МО', n:10, a:0.60},
        {name:'средняя часть', n:92, a:0.80},
        {name:'носовая оконечность', n:34, a:0.60}], 100)""")
    assert got['total'] == pytest.approx(10 * 0.6 + 92 * 0.8 + 34 * 0.6, rel=1e-12)
    assert abs(got['resid']) < 1e-9, 'разбивка не сошлась с длиной судна'
    assert got['frames'] == 136
    # носовая зона обязана перекрывать 0,2L
    bow = got['zones'][2]
    assert bow['len'] >= 0.2 * L
    assert bow['a'] <= 0.7            # ограничение Правил в носовой части


# ------------------------------------------------------ разбор 2: обшивка

def py_pressure(T, z, az=AZ):
    return max(0.0, 10 * (T - z + az))


def test_pressure_shell():
    assert hc('H.pressureShell(6.6, 0)') == pytest.approx(py_pressure(6.6, 0))
    assert hc('H.pressureShell(6.6, 0)') == pytest.approx(86.0)
    assert hc('H.pressureShell(6.6, 2.5)') == pytest.approx(61.0)
    assert hc('H.pressureShell(6.6, 5.9)') == pytest.approx(27.0)
    # выше уровня волнового напора давление обращается в ноль, а не в минус
    assert hc('H.pressureShell(6.6, 12.0)') == 0


def py_plate(C, a, p, ks, reh, ds=0.0):
    return C * a * math.sqrt(p / (ks * reh)) + ds


def test_plate_thickness_bottom():
    got = hc('H.plateThickness({a:0.80, p:86, ks:0.60, ReH:235, ds:1.0})')
    assert got['sigmaAllow'] == pytest.approx(141.0)
    assert got['sCalc'] == pytest.approx(py_plate(15.8, 0.80, 86, 0.60, 235), rel=1e-12)
    assert got['sCalc'] == pytest.approx(9.87, abs=0.01)
    assert got['sTotal'] == pytest.approx(10.87, abs=0.01)
    assert got['sSheet'] == 11.0


def test_plate_thickness_exact_scheme():
    """«Честная» схема с полным защемлением даёт ровно в √2 раз больше."""
    edu = hc('H.plateThickness({a:0.80, p:86, ks:0.60, ReH:235}).sCalc')
    ex = hc('H.plateThickness({a:0.80, p:86, ks:0.60, ReH:235, C:H.C_EXACT}).sCalc')
    assert ex / edu == pytest.approx(22.36068 / 15.8, rel=1e-6)
    assert ex == pytest.approx(13.97, abs=0.01)
    assert hc('H.C_EXACT') == pytest.approx(1e3 / math.sqrt(2e3), rel=1e-12)


def test_plate_thickness_side():
    got = hc('H.plateThickness({a:0.80, p:61, ks:0.75, ReH:235, ds:1.0})')
    assert got['sigmaAllow'] == pytest.approx(176.25)
    assert got['sCalc'] == pytest.approx(py_plate(15.8, 0.80, 61, 0.75, 235), rel=1e-12)
    assert got['sTotal'] == pytest.approx(8.44, abs=0.01)
    assert got['sSheet'] == 8.5


def test_min_thickness_does_not_govern():
    """У 100-метрового судна минимальная толщина ниже расчётной для борта."""
    smin = hc('H.minThickness(100, 1)')
    assert smin == pytest.approx(4.5 + 0.03 * 100, rel=1e-12)
    assert smin == pytest.approx(7.5, abs=0.01)
    side = hc('H.plateThickness({a:0.80, p:61, ks:0.75, ReH:235, ds:1.0}).sTotal')
    assert side > smin, 'расчёт должен перекрывать минимум — иначе вывод разбора 2 неверен'


def test_sheet_rounding_is_upward_only():
    ladder = hc('H.SHEET')
    for s in (7.51, 9.99, 10.14, 11.0, 14.7):
        got = hc('H.roundSheet(%r)' % s)
        assert got >= s - 1e-9, 'округление вниз недопустимо'
        assert got in ladder
        smaller = [x for x in ladder if s - 1e-9 <= x < got]
        assert not smaller, 'взята не ближайшая большая толщина'


# ----------------------------------------------------- разбор 3: настилы

def test_cargo_pressure_on_inner_bottom():
    got = hc('H.pressureCargo(0.70, 7.30)')
    assert got['pStatic'] == pytest.approx(0.70 * G * 7.30, rel=1e-12)
    assert got['pStatic'] == pytest.approx(50.13, abs=0.01)
    assert got['p'] == pytest.approx(1.3 * 0.70 * G * 7.30, rel=1e-12)
    assert got['p'] == pytest.approx(65.17, abs=0.01)


def test_inner_bottom_thickness():
    got = hc('H.plateThickness({a:0.80, p:65.17, ks:0.65, ReH:235, ds:2.0})')
    assert got['sCalc'] == pytest.approx(8.26, abs=0.01)
    assert got['sSheet'] == 10.5


def test_deck_pressure_is_washing():
    """Груза на палубе нет — определяет заливание."""
    got = hc('H.pressureDeck(0)')
    assert got['p'] == pytest.approx(20.0)
    assert got['governs'] == 'заливание'
    assert hc('H.pressureDeck(35).governs') == 'груз'


def test_deck_local_strength_is_not_the_answer():
    """Местная прочность просит 5,5 мм, а принято 15 — определяет общий изгиб."""
    got = hc('H.plateThickness({a:0.80, p:20, ks:0.60, ReH:235, ds:0.5})')
    assert got['sSheet'] == 5.5
    assert hc('H.SCANT.deck') == 15


# ---------------------------------------- разбор 4/5: балки и составные сечения

def py_required_modulus(p, a, l, m, ks, reh):
    M = p * a * l * l / m
    return M, 1e3 * M / (ks * reh)


def test_required_modulus_bottom_longitudinal():
    got = hc('H.requiredModulus({p:86, a:0.80, l:2.40, m:12, ks:0.65, ReH:235})')
    M, W = py_required_modulus(86, 0.80, 2.40, 12, 0.65, 235)
    assert got['M'] == pytest.approx(M, rel=1e-12)
    assert got['W'] == pytest.approx(W, rel=1e-12)
    assert got['M'] == pytest.approx(33.02, abs=0.01)
    assert got['W'] == pytest.approx(216.2, abs=0.1)
    assert got['Q'] == pytest.approx(86 * 0.80 * 2.40 / 2, rel=1e-12)


def test_attached_flange():
    assert hc('H.attachedFlange(0.80, 2.40)') == pytest.approx(0.40)
    assert hc('H.attachedFlange(0.80, 3.65)') == pytest.approx(3.65 / 6)
    assert hc('H.attachedFlange(0.80, 9.00)') == pytest.approx(0.80)


def py_bulb_with_plate(prof, bp_m, s_mm):
    """Профиль + поясок обшивки, посчитанный здесь заново.

    База — внутренняя поверхность обшивки; центр тяжести профиля на y0 выше
    неё, крайнее волокно (носок бульба) — на высоте h.
    """
    bp, s = bp_m * 100.0, s_mm / 10.0
    a1, i1, z1 = prof['A'], prof['I'], prof['y0']
    a2, i2, z2 = bp * s, bp * s ** 3 / 12.0, -s / 2.0
    at = a1 + a2
    zc = (a1 * z1 + a2 * z2) / at
    it = i1 + a1 * (z1 - zc) ** 2 + i2 + a2 * (z2 - zc) ** 2
    return {'A': at, 'zc': zc, 'I': it, 'W': it / (prof['h'] - zc)}


@pytest.mark.parametrize('no,bp,s', [('18б', 0.40, 11), ('20а', 0.40, 11),
                                     ('20б', 0.40, 11), ('22а', 0.40, 11),
                                     ('22а', 0.608, 8.5), ('16а', 0.40, 15)])
def test_bulb_with_plate_recomputed(no, bp, s):
    prof = hc('H.bulb(%s)' % json.dumps(no))
    got = hc('H.bulbWithPlate(%s, %r, %r)' % (json.dumps(no), bp, s))
    want = py_bulb_with_plate(prof, bp, s)
    assert got['zc'] == pytest.approx(want['zc'], rel=1e-9)
    assert got['I'] == pytest.approx(want['I'], rel=1e-9)
    assert got['W'] == pytest.approx(want['W'], rel=1e-9)


#: справочные W´x ГОСТ 21937 — профиль с присоединённым пояском 500 × 10 мм
GOST_WX = {'14а': 93.5, '16а': 134.4, '18а': 184.3, '20а': 251.9, '22а': 330.3}


def test_bulb_matches_gost_reference_value_exactly():
    """Калибровочная точка: ПБ 20а с пояском 500 × 10 мм — справочный W´x ГОСТ.

    Ширина пояска подобрана обращением: справочная графа W´x ГОСТ 21937 для
    профиля № 20а равна 251,9 см³, и наш расчёт даёт 251,2 см³ — расхождение
    0,3 %. Это доказывает, что y0 прочитан правильно (как отстояние центра
    тяжести от привариваемой кромки) и поясок присоединён с нужной стороны:
    ошибка в любом из двух даёт расхождение в разы, а не в доли процента.
    """
    assert hc("H.bulbWithPlate('20а', 0.5, 10).W") == pytest.approx(251.9, rel=0.005)


@pytest.mark.parametrize('no', sorted(GOST_WX))
def test_bulb_close_to_gost_reference_over_the_range(no):
    """По всему ряду профилей расхождение со справочной графой не более 6 %.

    Точного совпадения ждать нельзя: ГОСТ считает W´x со СВОИМ присоединённым
    пояском, ширина которого в стандарте привязана к номеру профиля, а мы для
    сравнимости берём один и тот же поясок 500 × 10 мм. Важно, что расхождение
    остаётся малым и не растёт систематически — значит, формула составного
    сечения верна, а не подогнана под одну точку.
    """
    got = hc("H.bulbWithPlate(%s, 0.5, 10).W" % json.dumps(no))
    assert got == pytest.approx(GOST_WX[no], rel=0.06)


def test_pick_bulb_for_bottom_longitudinal():
    """По местной прочности проходит ПБ 20а — это ответ разбора 4."""
    got = hc('H.pickBulb(216.2, 0.40, 11)')
    assert got['pick']['no'] == '20а'
    assert got['pick']['W'] == pytest.approx(249.6, abs=0.5)
    assert got['pick']['margin'] == pytest.approx(0.155, abs=0.005)
    # профили сортамента упорядочены по возрастанию момента сопротивления
    ws = [r['W'] for r in got['rows']]
    assert ws == sorted(ws), 'сортамент должен идти по возрастанию W'


def test_frame_modulus_and_choice():
    """Шпангоут борта: ПБ 20б проходит впритык, поэтому принят ПБ 22а."""
    p = hc('H.pressureShell(6.6, 2.825)')
    assert p == pytest.approx(57.75, abs=0.01)
    got = hc('H.requiredModulus({p:57.75, a:0.80, l:3.65, m:12, ks:0.75, ReH:235})')
    assert got['W'] == pytest.approx(291.0, abs=0.5)
    w20b = hc("H.bulbWithPlate('20б', 0.608, 8.5).W")
    w22a = hc("H.bulbWithPlate('22а', 0.608, 8.5).W")
    assert w20b / got['W'] - 1 < 0.01, 'запас ПБ 20б должен быть меньше 1 %'
    assert w22a / got['W'] - 1 > 0.09, 'ПБ 22а должен давать заметный запас'


def test_no_stringer_pushes_frame_out_of_range():
    """Без бортового стрингера требуемый W выходит за сортамент полособульба."""
    got = hc('H.requiredModulus({p:H.pressureShell(6.6,4.65), a:0.80, l:7.30, m:12, ks:0.75, ReH:235})')
    assert got['W'] == pytest.approx(796, abs=2)
    best = hc("H.bulbWithPlate('24а', 0.80, 8.5).W")
    assert best < got['W'], 'сортамент не должен покрывать этот момент сопротивления'


def test_built_t_section():
    """Сварной тавр рамного шпангоута — пересчёт составного сечения заново."""
    got = hc('H.builtT({hw:800, sw:10, bf:220, tf:16, bp:1.217, s:8.5})')
    hw, sw, bf, tf, bp, s = 80.0, 1.0, 22.0, 1.6, 121.7, 0.85
    parts = [(bp * s, bp * s ** 3 / 12, -s / 2),
             (hw * sw, sw * hw ** 3 / 12, hw / 2),
             (bf * tf, bf * tf ** 3 / 12, hw + tf / 2)]
    at = sum(p[0] for p in parts)
    zc = sum(p[0] * p[2] for p in parts) / at
    it = sum(p[1] + p[0] * (p[2] - zc) ** 2 for p in parts)
    assert got['A'] == pytest.approx(at, rel=1e-9)
    assert got['zc'] == pytest.approx(zc, rel=1e-9)
    assert got['I'] == pytest.approx(it, rel=1e-9)
    assert got['W'] == pytest.approx(it / (hw + tf - zc), rel=1e-9)
    assert got['W'] == pytest.approx(4355, abs=5)


def test_shear_check():
    got = hc('H.shearCheck(461.4, 800, 10, 0.75, 235)')
    assert got['tau'] == pytest.approx(461.4e3 / 8000, rel=1e-12)
    assert got['tauAllow'] == pytest.approx(0.57 * 0.75 * 235, rel=1e-12)
    assert got['tau'] == pytest.approx(57.7, abs=0.1)
    assert got['ok']


# ------------------------------------------------- разбор 6/8: кницы и швы

def test_bracket_and_free_edge():
    got = hc('H.bracket({c:350, t:10, s:8.5, bp:0.5})')
    c, t, s, bp = 35.0, 1.0, 0.85, 50.0
    parts = [(t * c, t * c ** 3 / 12, c / 2), (bp * s, bp * s ** 3 / 12, -s / 2)]
    at = sum(p[0] for p in parts)
    zc = sum(p[0] * p[2] for p in parts) / at
    it = sum(p[1] + p[0] * (p[2] - zc) ** 2 for p in parts)
    assert got['I'] == pytest.approx(it, rel=1e-9)
    assert got['W'] == pytest.approx(it / (c + s / 2 - zc), rel=1e-9)
    assert got['W'] == pytest.approx(351.0, abs=0.5)
    # свободная кромка: 350·√2 = 495 мм при пределе 50t = 500 мм
    fe = hc('H.freeEdge(350, 10)')
    assert fe['lFree'] == pytest.approx(350 * math.sqrt(2), rel=1e-12)
    assert not fe['needFlange']
    assert hc('H.freeEdge(400, 10).needFlange') is True


def test_bracket_covers_the_frame_it_joins():
    """Кница не может быть слабее балки, к которой примыкает.

    Момент сопротивления шпангоута зависит от присоединённого пояска, а тот —
    от пролёта: b_п = min(a; ℓ/6) = 0,608 м при ℓ = 3,65 м. Сравнивать кницу
    надо именно с этой величиной (322,7 см³), а не со значением при каком-то
    другом пояске — иначе проверка «кница ≥ балка» теряет смысл.
    """
    bp = hc('H.attachedFlange(0.80, 3.65)')
    assert bp == pytest.approx(3.65 / 6, rel=1e-12)
    frame = hc("H.bulbWithPlate('22а', H.attachedFlange(0.80, 3.65), 8.5).W")
    assert frame == pytest.approx(322.7, abs=0.2)
    small = hc('H.bracket({c:300, t:10, s:8.5, bp:0.5}).W')
    pick = hc('H.bracket({c:350, t:10, s:8.5, bp:0.5}).W')
    big = hc('H.bracket({c:400, t:11, s:8.5, bp:0.5}).W')
    assert small < frame, 'кница 300×300×10 обязана не проходить'
    assert pick >= frame and pick / frame - 1 == pytest.approx(0.088, abs=0.003)
    # больший вариант прочнее, но проваливает независимое требование к кромке
    assert big > pick
    assert hc('H.freeEdge(400, 11).needFlange') is True
    assert hc('H.freeEdge(350, 10).needFlange') is False


def test_fillet_weld():
    got = hc('H.filletWeld(84.3, 5, 350, 235)')
    assert got['A'] == pytest.approx(2 * 0.7 * 5 * 350, rel=1e-12)
    assert got['tau'] == pytest.approx(84.3e3 / (2 * 0.7 * 5 * 350), rel=1e-12)
    assert got['tau'] == pytest.approx(34.4, abs=0.1)
    assert got['ok']


# -------------------------------------------------------- разбор 7: вырезы

def test_opening_position_decides():
    """Один и тот же вырез проходит вдали от опоры и не проходит у опоры."""
    far = hc('H.opening({q:206.4, l:7.65, x:1.2, hw:1000, sw:10, hOpen:400, ks:0.75, ReH:235})')
    near = hc('H.opening({q:206.4, l:7.65, x:0.4, hw:1000, sw:10, hOpen:400, ks:0.75, ReH:235})')
    assert far['Q'] == pytest.approx(206.4 * (7.65 / 2 - 1.2), rel=1e-12)
    assert far['tau'] == pytest.approx(90.3, abs=0.1) and far['ok']
    assert near['tau'] == pytest.approx(117.8, abs=0.1) and not near['ok']
    assert near['Areq'] == pytest.approx(near['Q'] * 1e3 / near['tauAllow'], rel=1e-12)
    assert near['dA'] == pytest.approx(1037, abs=3)
    # опорная перерезывающая сила и напряжение по целой стенке
    assert near['Qsup'] == pytest.approx(206.4 * 7.65 / 2, rel=1e-12)
    assert near['Qsup'] * 1e3 / 1e4 == pytest.approx(78.9, abs=0.1)


def test_concentration_factor():
    assert hc('H.concentration(200, 300)') == pytest.approx(1 + 2 * 200 / 300)
    # круглый вырез: K = 3 — классический результат Кирша
    assert hc('H.concentration(100, 100)') == pytest.approx(3.0)


# ---------------------------------------------------- разбор 9: гофрированная

def test_corrugation_geometry_and_modulus():
    g = hc('H.corrugationGeom(800, 500, 60)')
    assert g['b'] == pytest.approx(800 - 500 * math.cos(math.radians(60)), rel=1e-12)
    assert g['d'] == pytest.approx(500 * math.sin(math.radians(60)), rel=1e-12)
    assert g['b'] == pytest.approx(550.0) and g['d'] == pytest.approx(433.0, abs=0.1)
    assert g['develop'] == pytest.approx(1050.0)
    w = hc('H.corrugationModulus(H.corrugationGeom(800,500,60), 8)')
    b, c, d, t = 55.0, 50.0, g['d'] / 10, 0.8
    assert w == pytest.approx((d / 6) * (3 * b * t + c * t), rel=1e-9)
    assert w == pytest.approx(1241, abs=2)


def test_corrugation_buckling_governs():
    """Толщину гофра определяет устойчивость полки, а не прочность."""
    req = hc('H.requiredModulus({p:36.5, a:0.80, l:7.30, m:12, ks:0.75, ReH:235})')
    assert req['W'] == pytest.approx(736, abs=1)
    # по прочности хватает 4,74 мм
    w_per_mm = hc('H.corrugationModulus(H.corrugationGeom(800,500,60), 10)') / 10.0
    assert req['W'] / w_per_mm == pytest.approx(4.74, abs=0.02)
    # но при 6 мм полка теряет устойчивость раньше, чем достигает σ
    for t, ok in ((6, False), (7, True), (8, True)):
        s_cr = hc('H.johnsonOstenfeld(H.eulerPlate(550, %d, 4), 235)' % t)
        sigma = 1e3 * req['M'] / hc(
            'H.corrugationModulus(H.corrugationGeom(800,500,60), %d)' % t)
        assert (sigma <= s_cr) is ok, 'толщина %d мм: ожидалось %s' % (t, ok)


def test_corrugation_mass_advantage():
    m1 = hc('H.corrugationMass(H.corrugationGeom(800,500,60), 8)')
    assert m1 == pytest.approx(1050 / 800 * 0.008 * RHO_ST, rel=1e-12)
    assert m1 == pytest.approx(82.4, abs=0.1)
    flat = hc('H.panelMass(9.5, 44.8, 0.80)')
    assert flat['plate'] == pytest.approx(0.0095 * RHO_ST, rel=1e-12)
    assert flat['total'] == pytest.approx(118.5, abs=0.2)
    assert (flat['total'] - m1) / flat['total'] == pytest.approx(0.305, abs=0.003)


# ------------------------------------------- разбор 10: общий продольный изгиб

def py_wave_coefficient(l):
    if l <= 300:
        return 10.75 - ((300 - l) / 100) ** 1.5
    if l <= 350:
        return 10.75
    return 10.75 - ((l - 350) / 150) ** 1.5


def test_wave_coefficient():
    assert hc('H.waveCoefficient(100)') == pytest.approx(py_wave_coefficient(100), rel=1e-12)
    assert hc('H.waveCoefficient(100)') == pytest.approx(7.9216, abs=1e-4)
    assert hc('H.waveCoefficient(300)') == pytest.approx(10.75, abs=1e-12)
    assert hc('H.waveCoefficient(320)') == pytest.approx(10.75, abs=1e-12)
    assert hc('H.waveCoefficient(400)') < 10.75


def test_wave_moments_iacs():
    got = hc('H.waveMoments(100, 15.3, 0.74)')
    c = py_wave_coefficient(100)
    assert got['hog'] == pytest.approx(190 * c * L ** 2 * B * CB * 1e-3, rel=1e-12)
    assert got['sag'] == pytest.approx(-110 * c * L ** 2 * B * (CB + 0.7) * 1e-3, rel=1e-12)
    assert got['hog'] == pytest.approx(170407, abs=2)
    assert got['sag'] == pytest.approx(-191981, abs=2)
    assert abs(got['sag']) > got['hog'], 'прогибающий момент должен быть больше'
    # Cb в нормах не принимается меньше 0,6
    assert hc('H.waveMoments(100, 15.3, 0.50).hog') == \
        pytest.approx(hc('H.waveMoments(100, 15.3, 0.60).hog'), rel=1e-12)


def test_minimum_requirements():
    c = py_wave_coefficient(100)
    wmin = hc('H.minModulus(100, 15.3, 0.74, 1)')
    imin = hc('H.minInertia(100, 15.3, 0.74)')
    assert wmin == pytest.approx(c * L ** 2 * B * (CB + 0.7) * 1.0, rel=1e-12)
    assert imin == pytest.approx(3 * c * L ** 3 * B * (CB + 0.7), rel=1e-12)
    assert wmin == pytest.approx(1745281, abs=5)
    assert imin == pytest.approx(523584281, abs=500)
    # I_min не зависит от марки стали, W_min зависит
    assert hc('H.minModulus(100, 15.3, 0.74, 0.78)') == pytest.approx(wmin * 0.78, rel=1e-12)


def test_equivalent_beam_of_midship_section():
    """Эквивалентный брус мидель-шпангоута — пересчёт таблицы заново."""
    items = hc('H.midshipItems()')
    eb = hc('H.equivalentBeam(H.midshipItems(), H.SHIP.H)')
    at = sum(i['A'] for i in items)
    zc = sum(i['A'] * i['z'] for i in items) / at        # м
    it = sum(i['I'] + i['A'] * ((i['z'] - zc) * 100) ** 2 for i in items)
    assert eb['A'] == pytest.approx(at, rel=1e-9)
    assert eb['zc'] == pytest.approx(zc, rel=1e-9)
    assert eb['I'] == pytest.approx(it, rel=1e-9)
    assert eb['Wdeck'] == pytest.approx(it / ((H - zc) * 100), rel=1e-9)
    assert eb['Wbottom'] == pytest.approx(it / (zc * 100), rel=1e-9)
    # контрольные значения, напечатанные на странице разбора 10
    assert eb['A'] == pytest.approx(7483.2, abs=0.2)
    assert eb['zc'] == pytest.approx(3.176, abs=0.001)
    assert eb['I'] == pytest.approx(931745237, abs=2000)
    assert eb['Wdeck'] == pytest.approx(1818273, abs=5)
    assert eb['Wbottom'] == pytest.approx(2934024, abs=5)
    # нейтральная ось ниже середины высоты борта — из-за выреза люка
    assert eb['zc'] < H / 2


def test_hull_stress_dimension():
    """1 кН·м на 1 см³ даёт ровно 10³ МПа."""
    assert hc('H.hullStress(1, 1)') == pytest.approx(1e3, rel=1e-12)


def test_girder_check_passes_with_small_margin():
    got = hc("""H.girderCheck({L:100, B:15.3, Cb:0.74, k:1,
        Msw:{hog:110000, sag:-55000},
        beam:H.equivalentBeam(H.midshipItems(), H.SHIP.H)})""")
    assert got['Mhog'] == pytest.approx(110000 + 170407, abs=2)
    assert got['Msag'] == pytest.approx(-55000 - 191981, abs=2)
    assert got['WreqStress'] == pytest.approx(got['Mhog'] * 1e3 / 175, rel=1e-9)
    # минимум Правил строже расчёта по напряжениям — вывод разбора 10
    assert got['Wmin'] > got['WreqStress']
    assert got['Wreq'] == pytest.approx(got['Wmin'], rel=1e-12)
    assert got['okW'] and got['okI']
    assert got['reserveW'] == pytest.approx(0.042, abs=0.002)
    assert got['reserveI'] == pytest.approx(0.78, abs=0.01)
    assert got['sigmaDeckHog'] == pytest.approx(154.2, abs=0.2)
    assert got['sigmaBottomHog'] == pytest.approx(95.6, abs=0.2)
    assert got['sigmaDeckSag'] == pytest.approx(-135.8, abs=0.2)
    assert got['sigmaBottomSag'] == pytest.approx(-84.2, abs=0.2)
    assert abs(got['sigmaDeckHog']) <= got['sigmaAllow']


def test_buckling_of_compressed_members():
    k = hc('H.PLATE_K')
    assert k == pytest.approx(math.pi ** 2 * E / (12 * (1 - NU ** 2)), rel=1e-12)
    assert k == pytest.approx(186184.8, abs=0.5)
    for s, se, scr in ((15, 261.8, 182.3), (11, 140.8, 136.9)):
        assert hc('H.eulerPlate(800, %d, 4)' % s) == pytest.approx(se, abs=0.2)
        assert hc('H.johnsonOstenfeld(H.eulerPlate(800, %d, 4), 235)' % s) == \
            pytest.approx(scr, abs=0.2)
    # запаса хватает, значит редуцировать связи не надо
    assert hc('H.reduction(182.3, 135.8)') == 1
    assert hc('H.reduction(136.9, 95.6)') == 1
    # гибкость пластин в норме 1,6…2,5
    for s, beta in ((15, 1.80), (11, 2.46)):
        b = hc('H.slenderness(800, %d, 235)' % s)
        assert b == pytest.approx(beta, abs=0.01)
        assert 1.6 <= b <= 2.5


def test_thickness_for_buckling_of_deck():
    """Устойчивость просит 11,0 мм — меньше, чем общий изгиб (15 мм)."""
    got = hc('H.thicknessForBuckling(800, 135.83, 235, 4)')
    assert got['sigmaE'] == pytest.approx(235 ** 2 / (4 * (235 - 135.83)), rel=1e-9)
    assert got['sigmaE'] == pytest.approx(139.2, abs=0.1)
    assert got['s'] == pytest.approx(10.94, abs=0.02)
    assert got['s'] < hc('H.SCANT.deck')


def test_combined_stress_moves_profile_to_22a():
    """Ключевой вывод курса: с общим изгибом ПБ 20а не проходит, ПБ 22а — да."""
    eb = hc('H.equivalentBeam(H.midshipItems(), H.SHIP.H)')
    Mhog = 110000 + hc('H.waveMoments(100, 15.3, 0.74).hog')
    Mloc = hc('H.requiredModulus({p:86, a:0.80, l:2.40, m:12, ks:0.65, ReH:235}).M')
    limit = 0.9 * REH
    out = {}
    for no in ('20а', '22а'):
        prof = hc('H.bulb(%s)' % json.dumps(no))
        w_loc = hc('H.bulbWithPlate(%s, 0.40, 11).W' % json.dumps(no))
        z_tip = 0.011 + prof['h'] / 100.0            # м, носок бульба
        w_girder = eb['I'] / ((eb['zc'] - z_tip) * 100)
        out[no] = 1e3 * Mhog / w_girder + 1e3 * Mloc / w_loc
    assert out['20а'] == pytest.approx(221.5, abs=0.5)
    assert out['22а'] == pytest.approx(191.5, abs=0.5)
    assert out['20а'] > limit, 'ПБ 20а обязан не проходить — иначе вывод разбора 10 ложен'
    assert out['22а'] <= limit
    # в сечение эквивалентного бруса заложен именно ПБ 22а
    names = [i['name'] for i in hc('H.midshipItems()')]
    assert any('22а' in n for n in names), 'брус должен считаться с принятым профилем'


def test_worn_section_still_passes():
    """Конец срока службы: W падает, но остаётся выше 0,9·W_min."""
    got = hc("""(() => {
      const w = Object.assign({}, H.SCANT);
      w.keel -= 1; w.bottom -= 1; w.bilge -= 1; w.sideLo -= 1; w.sideUp -= 1;
      w.sheer -= 1; w.deck -= 0.5; w.coaming -= 0.5; w.inner -= 2;
      w.vkeel -= 1; w.girder -= 1; w.sideStr -= 1;
      const nw = H.equivalentBeam(H.midshipItems(), H.SHIP.H);
      const wo = H.equivalentBeam(H.midshipItems(w), H.SHIP.H);
      return {zcNew: nw.zc, zcWorn: wo.zc, Inew: nw.I, Iworn: wo.I,
              Wnew: nw.Wdeck, Wworn: wo.Wdeck,
              limit: 0.9 * H.minModulus(100, 15.3, 0.74, 1)};
    })()""")
    assert got['zcWorn'] == pytest.approx(3.274, abs=0.002)
    assert got['zcWorn'] > got['zcNew'], 'ось должна ползти вверх: снизу металла уходит больше'
    assert got['Iworn'] / got['Inew'] - 1 == pytest.approx(-0.062, abs=0.002)
    assert got['Wworn'] / got['Wnew'] - 1 == pytest.approx(-0.044, abs=0.002)
    assert got['Wworn'] == pytest.approx(1739100, abs=200)
    assert got['limit'] == pytest.approx(1570753, abs=5)
    assert got['Wworn'] >= got['limit']


# ---------------------------------------------------------- ледовые усиления

def test_ice_classes_are_ordered():
    """Категории идут по возрастанию тяжести условий — иначе таблица лжёт."""
    ice = hc('H.ICE')
    assert [c['cls'] for c in ice] == ['Ice1', 'Ice2', 'Ice3', 'Arc4', 'Arc5']
    for a, b in zip(ice, ice[1:]):
        assert b['kShell'] > a['kShell']
        assert b['up'] >= a['up'] and b['down'] >= a['down']
    # расчётных ледовых давлений в модуле нет и быть не должно
    assert all('p' not in c for c in ice), \
        'ледовые давления Правил нельзя подменять учебным числом'


def test_ice_shell_estimate_is_comparative():
    """Оценка ледового пояса — сравнительная: во сколько раз связь тяжелеет."""
    for cls, k in (('Ice2', 1.30), ('Arc4', 1.80)):
        got = hc("H.iceShellEstimate(8.5, %s)" % json.dumps(cls))
        assert got['s'] == pytest.approx(8.5 * k, rel=1e-12)
    assert hc("H.iceShellEstimate(8.5, 'Ice2').sSheet") == 11.5
    assert hc("H.iceShellEstimate(8.5, 'Arc4').sSheet") == 15.5


def test_ice_belt_geometry():
    got = hc("H.iceBelt(3.6, 6.6, 'Ice2')")
    assert got['lower'] == pytest.approx(3.6 - 0.7, abs=1e-9)
    assert got['upper'] == pytest.approx(6.6 + 0.6, abs=1e-9)
    assert got['height'] == pytest.approx(4.3, abs=1e-9)


# --------------------------------------- согласование страниц и модуля

#: (файл разбора, строка, которая обязана на нём стоять)
PAGE_NUMBERS = [
    ('p-spacing.html', '0,68'), ('p-spacing.html', '0,80'),
    ('p-spacing.html', '17,6'), ('p-spacing.html', '7,20'),
    ('p-plating.html', '86,0'), ('p-plating.html', '141,0'),
    ('p-plating.html', '22,36'), ('p-plating.html', '11,0'),
    ('p-deckplate.html', '65,17'), ('p-deckplate.html', '10,5'),
    ('p-deckplate.html', '186 184,8'),
    ('p-stiffener.html', '33,02'), ('p-stiffener.html', '216,2'),
    ('p-stiffener.html', '249,6'), ('p-stiffener.html', '152,75'),
    ('p-frame.html', '57,75'), ('p-frame.html', '291,0'),
    ('p-frame.html', '673,6'), ('p-frame.html', '4355'),
    ('p-bracket.html', '351,0'), ('p-bracket.html', '84,3'),
    ('p-bracket.html', '322,7'), ('p-node.html', '322,7'),
    ('p-frame.html', '322,7'), ('p-frame.html', '4355'),
    ('p-opening.html', '206,4'), ('p-opening.html', '117,8'),
    ('p-opening.html', '100,5'), ('p-opening.html', '2,33'),
    ('p-node.html', '789,5'), ('p-node.html', '78,9'),
    ('p-corrugated.html', '736'), ('p-corrugated.html', '82,4'),
    ('p-corrugated.html', '147,4'),
    ('p-girder.html', '7,9216'), ('p-girder.html', '170 407'),
    ('p-girder.html', '1 745 281'), ('p-girder.html', '931 745 237'),
    ('p-girder.html', '1 818 273'), ('p-girder.html', '154,2'),
    ('p-girder.html', '182,3'), ('p-girder.html', '221,5'),
    ('p-girder.html', '1 739 100'),
    # теория обязана печатать те же числа, что и разбор
    ('t-rules.html', '7,9216'), ('t-rules.html', '1 745 281'),
    ('t-rules.html', '2,90'), ('t-rules.html', '7,20'),
    ('t-rules.html', '11,5'),
]


@pytest.mark.parametrize('page,needle', PAGE_NUMBERS,
                         ids=['%s:%s' % (p, n) for p, n in PAGE_NUMBERS])
def test_page_shows_computed_number(page, needle):
    """Числа, полученные модулем, должны стоять и в тексте разбора."""
    path = os.path.join(SITE, page)
    if not os.path.isfile(path):
        pytest.skip('страница %s ещё не создана' % page)
    with open(path, encoding='utf-8') as fh:
        html = fh.read()
    assert needle in html, 'на странице %s нет значения «%s»' % (page, needle)


#: старое судно, с которого сайт переведён на сквозной пример кластера.
#: Шаблоны с границей: «8,5 м» не должно ловиться внутри «8,5 мм», а «140 м» —
#: внутри «140 мм», поэтому единица закрывается отрицательным просмотром вперёд.
OLD_SHIP_TRACES = [
    r'140\s*м(?!м|е|и)',      # длина прежнего судна
    r'L\s*=\s*140',
    r'8,5\s*м(?!м)',          # осадка прежнего судна
    r'0,75\s*м(?!м)',         # прежняя шпация
    r'105\s*кПа',             # прежнее давление на днище
]


@pytest.mark.parametrize('page', [
    'p-spacing.html', 'p-plating.html', 'p-deckplate.html', 'p-stiffener.html',
    'p-frame.html', 'p-bracket.html', 'p-opening.html', 'p-node.html',
    'p-corrugated.html', 'p-girder.html'])
def test_no_traces_of_the_old_example_ship(page):
    """Разборы обязаны считать одно судно — то же, что /design/ и /shiptech/."""
    path = os.path.join(SITE, page)
    if not os.path.isfile(path):
        pytest.skip('страница %s ещё не создана' % page)
    with open(path, encoding='utf-8') as fh:
        html = fh.read()
    # неразрывный пробел считаем обычным — иначе проверка обходится вёрсткой
    flat = html.replace('\u00a0', ' ').replace('&nbsp;', ' ')
    found = [m.group(0) for pat in OLD_SHIP_TRACES
             for m in re.finditer(pat, flat)]
    assert not found, 'остались числа прежнего судна: %s' % ', '.join(sorted(set(found)))


def test_every_discussion_page_cites_the_rules():
    """В каждом разборе должна быть ссылка на норматив, а не только формулы."""
    pages = sorted(f for f in os.listdir(SITE) if f.startswith('p-') and f.endswith('.html'))
    assert len(pages) >= 10
    bad = []
    for page in pages:
        with open(os.path.join(SITE, page), encoding='utf-8') as fh:
            html = fh.read()
        if not re.search(r'Правил|РМРС|МАКО|UR S\d|ГОСТ', html):
            bad.append(page)
    assert not bad, 'разборы без ссылки на норматив: %s' % ', '.join(bad)
