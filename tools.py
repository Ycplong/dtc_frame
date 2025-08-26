import copy
import logging
import math
import os
import random
import datetime
import string
import sys
import threading

from tifffile import imwrite
import cv2
import numpy as np
# from common.util import SimpleFlaskLogger
import re

base_dir = os.path.dirname(os.path.dirname(__file__))

# tool_logger = SimpleFlaskLogger()
# 共享存储设置
# SHARED_STORAGE_PATH = os.path.join(base_dir,'shared_storage')
# print(SHARED_STORAGE_PATH)
SHARED_STORAGE_PATH = '/shared_storage'
lock = threading.Lock()

DEFECT_LOOKUP_TABLE = {
    0: "a",
    1: "b",
    2: "c",
    3: "d",
    4: "e",
    5: "f",
    6: "g",
    7: "h",
    8: "i",
    9: "j",
    10: "k",
    11: "l",
    12: "m",
    13: "n",
    14: "o",
    15: "p",
    16: "q",
    17: "r",
    18: "s",
    19: "t",
    20: "u",
    21: "v",
    22: "w",
    23: "x",
    24: "y",
    25: "z",
}

_MIN_DOT_RADIUS = 10 / 680
_MAX_DOT_RADIUS = 30 / 680

_MIN_BLOB_RADIUS = 15 / 680
_MAX_BLOB_RADIUS = 45 / 680
_MIN_BLOB_THICKNESS = 3 / 680
_MAX_BLOB_THICKNESS = 9 / 680

_MIN_SCRATCH_N = 2 / 680
_MAX_SCRATCH_N = 10 / 680
_MIN_SCRATCH_LENGTH = 30 / 680
_MAX_SCRATCH_LENGTH = 90 / 680

_MIN_TRIANGLE_BIAS = 15 / 680
_MAX_TRIANGLE_BIAS = 40 / 680

sampletestplan = """SampleTestPlan 72
  -1 1
  -5 2
  -4 1
  -2 3
  -8 6
  2 -7
  0 -8
  9 4
  -1 8
  6 -4
  -3 6
  10 -1
  6 -6
  -8 -4
  5 0
  5 -2
  3 -8
  1 -8
  -3 -3
  7 -3
  4 8
  -7 4
  3 -6
  8 -1
  2 4
  -4 2
  -8 -3
  5 -4
  9 3
  -2 -2
  1 -3
  0 4
  -2 7
  2 -2
  -3 -8
  6 1
  6 -5
  5 6
  4 3
  0 -1
  -3 4
  -5 1
  -4 -3
  0 9
  4 -5
  -8 -2
  -7 2
  7 -1
  -8 3
  -6 -3
  -1 -1
  9 -3
  4 -2
  5 3
  -2 4
  -8 4
  -8 5
  -7 6
  9 2
  -9 3
  -10 -1
  -9 2
  -10 -2
  10 0
  -10 -3
  -9 1
  9 1
  -9 0
  10 1
  10 -2
  -10 0
  8 5 ;
AreaPerTest 2.3996800474e+010;"""

frequency = [8.167e-2, 1.492e-2, 2.782e-2, 4.253e-2, 12.702e-2, 2.228e-2, 2.015e-2, 6.094e-2, 6.966e-2, 0.153e-2,
             0.772e-2, 4.025e-2, 2.406e-2, 6.749e-2, 7.507e-2, 1.929e-2, 0.095e-2, 5.987e-2, 6.327e-2, 9.056e-2,
             2.758e-2, 0.978e-2, 2.360e-2, 0.150e-2, 1.974e-2, 0.074e-2]

fonts = [cv2.FONT_HERSHEY_SIMPLEX, cv2.FONT_HERSHEY_PLAIN, cv2.FONT_HERSHEY_DUPLEX, cv2.FONT_HERSHEY_COMPLEX,
         cv2.FONT_HERSHEY_TRIPLEX, cv2.FONT_HERSHEY_SCRIPT_SIMPLEX]

char_size = [(round(random.random() * 2) + 1) / 1 for _ in range(26)]


def add_black_dot(img, radius=3):
    """
    图片中加入黑点

    :param img: 图片
    :param radius: 黑点半径
    :return: 加入黑点的图片
    """
    height = img.shape[0]
    width = img.shape[1]

    img_dot = copy.deepcopy(img)

    cv2.circle(img_dot, (height // 2, width // 2), radius, color=(0, 0, 0), thickness=-1)

    return img_dot


def add_blob(img, radius=15, thickness=3):
    """
    图片中加入圆圈

    :param img: 图片
    :param radius: 圆圈半径
    :param thickness: 圆圈厚度
    :return: 加入圆圈的图片
    """
    height = img.shape[0]
    width = img.shape[1]

    img_blob = copy.deepcopy(img)

    cv2.circle(img_blob, (height // 2, width // 2), radius, color=(0, 0, 0), thickness=thickness)

    return img_blob


def add_scratch(img, n=3, length=15, direction=0.0):
    """
    图片中加入划痕

    :param img: 图片
    :param n: 划痕数量
    :param length: 划痕长度
    :param direction: 划痕方向
    :return: 加入划痕的图片
    """
    height = img.shape[0]
    width = img.shape[1]

    p0 = (int(height / 2 + (length / 2) * math.cos(direction)), int(width / 2 + (length / 2) * math.sin(direction)))
    p1 = (int(p0[0] - length * math.cos(direction)), int(p0[1] - length * math.sin(direction)))

    img_scratch = copy.deepcopy(img)

    for i in range(n):
        shift_x = int(random.randrange(3, 5) * (i + 1 // 2) * pow(-1, i))
        shift_y = int(random.randrange(3, 5) * (i + 1 // 2) * pow(-1, i))
        cv2.line(
            img_scratch, (p0[0] + shift_x, p0[1] + shift_y), (p1[0] + shift_x, p1[1] + shift_y), color=(50, 50, 50)
        )

    return img_scratch


def add_triangle(img, radius=10):
    """
    图片中加入三角形

    :param img: 图片
    :param radius: 半径
    :return: 加入三角形的图片
    """
    height = img.shape[0]
    width = img.shape[1]

    points = list()
    angles = list()

    while len(angles) < 3:
        angle = random.random() * 2 * math.pi

        for a in angles:
            if abs(a - angle) < 45 / 180 * math.pi or abs(abs(a - angle) - math.pi) < 45 / 180 * math.pi:
                break
        else:
            angles.append(angle)

    for angle in angles:
        p_x = int(height // 2 + radius * math.cos(angle))
        p_y = int(width // 2 + radius * math.sin(angle))

        points.append((p_x, p_y))

    pts = np.array(points, np.int32)
    img_triangle = copy.deepcopy(img)
    cv2.fillPoly(img_triangle, [pts], color=(0, 0, 0))

    return img_triangle


def generate_defect_image(reference, defect_type, shot_size):
    """
    生成有缺陷的图片（修复601/602映射字母的逻辑）
    :param reference: 参考图片
    :param defect_type: 缺陷类型（601/602，符合需求的ClassLookup）
    :param shot_size: 截图大小
    :return: 有缺陷的图片
    """
    # 黑点
    if defect_type == 'black_dot':
        radius = random.uniform(_MIN_DOT_RADIUS * shot_size, _MAX_DOT_RADIUS * shot_size)
        defect_image = add_black_dot(reference, int(radius))
    # 圆圈
    elif defect_type == 'blob':
        radius = random.uniform(_MIN_BLOB_RADIUS * shot_size, _MAX_BLOB_RADIUS * shot_size)
        thickness = random.uniform(_MIN_BLOB_THICKNESS * shot_size, _MAX_BLOB_THICKNESS * shot_size)
        defect_image = add_blob(reference, int(radius), int(thickness))
    # 划痕
    elif defect_type == 'scratch':
        n = random.uniform(_MIN_SCRATCH_N * shot_size, _MAX_SCRATCH_N * shot_size)
        length = random.uniform(_MIN_SCRATCH_LENGTH * shot_size, _MAX_SCRATCH_LENGTH * shot_size)
        direction = random.random() * math.pi * 2
        defect_image = add_scratch(reference, int(n), int(length), direction)
    # 三角形
    elif defect_type == 'triangle':
        radius = random.uniform(_MIN_TRIANGLE_BIAS * shot_size, _MAX_TRIANGLE_BIAS * shot_size)
        defect_image = add_triangle(reference, int(radius))
    # 无缺陷
    elif defect_type == 'False':
        defect_image = copy.deepcopy(reference)
    # 关键修改：601→0（a），602→1（b），映射后再生成字母
    elif defect_type in [601, 602]:
        # 建立601/602与字母索引的映射（601=a→0，602=b→1）
        letter_index = 0 if defect_type == 601 else 1
        defect_image = generate_alphabets(reference, letter_index, shot_size)
    # 类型错误
    else:
        raise ValueError(f"Unknown defect type: {defect_type}（仅支持601/602或black_dot/blob/scratch/triangle）")
    return defect_image

def generate_alphabets(reference, defect_type, shot_size):
    font = random.choice(fonts)
    font_size = shot_size / 680 * 15

    thickness = int(round(random.random() * 1)) + 1
    cv2.putText(
        reference,
        string.ascii_lowercase[defect_type],
        (shot_size // 2, shot_size // 2),
        font,
        font_size,
        (0, 0, 0),
        thickness
    )

    return reference


def get_shot(background, center, img_size=40):
    return copy.deepcopy(background[center[0] - img_size // 2:center[0] + img_size // 2,
                         center[1] - img_size // 2:center[1] + img_size // 2])


def generate_topograph(img, direction, ratio=0.5):
    """
    生成X射线物相照片

    :param img: 图片
    :param direction: 方向
    :param ratio: 比值
    :return:
    """

    img_gray = copy.deepcopy(img)

    img_x = cv2.Sobel(img_gray, cv2.CV_16S, 1, 0)
    img_y = cv2.Sobel(img_gray, cv2.CV_16S, 0, 1)
    cos_value = math.cos(direction)
    sin_value = math.sin(direction)

    if cos_value >= 0:
        _, img_x = cv2.threshold(img_x, 0, 255, cv2.THRESH_TOZERO)
    else:
        _, img_x = cv2.threshold(img_x, 0, 255, cv2.THRESH_TOZERO_INV)
    img_blur_x = cv2.GaussianBlur(img_x, (9, 9), cv2.BORDER_DEFAULT)

    if sin_value >= 0:
        _, img_y = cv2.threshold(img_y, 0, 255, cv2.THRESH_TOZERO)
    else:
        _, img_y = cv2.threshold(img_y, 0, 255, cv2.THRESH_TOZERO_INV)
    img_blur_y = cv2.GaussianBlur(img_y, (9, 9), cv2.BORDER_DEFAULT)

    img_blur = ratio * (cos_value * img_blur_x + sin_value * img_blur_y)

    img_topograph = img_gray.astype('float') + img_blur
    _, img_topograph = cv2.threshold(img_topograph, 255, 255, cv2.THRESH_TRUNC)
    img_topograph = img_topograph.astype('uint8')

    return img_topograph


def generate_material(img, ratio=0.5):
    """
    生成基础图片

    :param img: 图片
    :param ratio: 比值
    :return: 基础图片
    """
    img_gray = copy.deepcopy(img)
    img_edge = cv2.Laplacian(img_gray, cv2.CV_16S, ksize=3)
    img_edge_abs = cv2.convertScaleAbs(img_edge)
    img_edge_blur = cv2.GaussianBlur(img_edge_abs, (9, 9), cv2.BORDER_DEFAULT)

    img_material = img_gray.astype('float') + ratio * img_edge_blur
    _, img_material = cv2.threshold(img_material, 255, 255, cv2.THRESH_TRUNC)
    img_material.astype('uint8')

    return img_material


def center_zoom(img, ratio=1.5):
    """
    生成中心聚焦图片

    :param img: 图片
    :param ratio: 比值
    :return: 中心聚焦图片
    """
    origin_height, origin_width = img.shape[0], img.shape[1]
    zoom_height, zoom_width = int(origin_height / ratio), int(origin_width / ratio)
    img_crop = img[(origin_height - zoom_height) // 2:(origin_height + zoom_height) // 2,
               (origin_width - zoom_width) // 2:(origin_width + zoom_width) // 2]
    img_resize = cv2.resize(img_crop, (origin_width, origin_height))
    return img_resize


def generate_defect_image_group(reference, defect_type, img_type, shot_size):
    """
    生成一组缺陷图片

    :param reference: 参考图片
    :param defect_type: 缺陷类型
    :param img_type: 图片类型
    :param shot_size: 截图大小
    :return: 一组缺陷图片
    """

    image_group = list()

    if img_type == "AOI":
        defect_image = generate_defect_image(reference, defect_type, shot_size)
        image_group.append(defect_image)

    elif img_type == "SEM":
        defect_image = generate_defect_image(reference, defect_type, shot_size)
        reference_image_sem = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
        defect_image_sem = cv2.cvtColor(defect_image, cv2.COLOR_BGR2GRAY)

        image_defect_topo_1 = generate_topograph(defect_image_sem, 0)
        image_defect_topo_2 = generate_topograph(defect_image_sem, math.pi)
        image_defect_topo_3 = generate_material(defect_image_sem)

        image_reference_topo_1 = generate_topograph(reference_image_sem, 0)
        image_reference_topo_2 = generate_topograph(reference_image_sem, math.pi)
        image_reference_topo_3 = generate_material(reference_image_sem)

        image_class_topo_1 = center_zoom(image_defect_topo_1)
        image_class_topo_2 = center_zoom(image_defect_topo_2)
        image_class_topo_3 = center_zoom(image_defect_topo_3)

        image_group.extend(
            [
                image_defect_topo_1, image_defect_topo_2, image_defect_topo_3,
                image_reference_topo_1, image_reference_topo_2, image_reference_topo_3,
                image_class_topo_1, image_class_topo_2, image_class_topo_3
            ]
        )

    else:
        raise ValueError("Unknown image type: {}".format(img_type))

    return image_group


def turn_list(x_list):
    """
    转动列表

    :param x_list: 列表
    :return:
    """

    x_list.append(x_list[0])
    x_list.pop(0)


def get_reference(template, shot_size):
    x = random.randrange(shot_size[1] // 2, template.shape[0] - shot_size[1] // 2)
    y = random.randrange(shot_size[0] // 2, template.shape[1] - shot_size[0] // 2)
    return copy.deepcopy(
        template[x - shot_size[1] // 2:x + shot_size[1] // 2, y - shot_size[0] // 2:y + shot_size[0] // 2])


def generate_klarf_header(klarf_file, klarf_info, machine_name, tiff_filename):
    # tool_logger.INFO("generate_klarf_header")
    add_klarf_content(klarf_file, 'FileVersion 1 2;')
    add_klarf_content(klarf_file, 'FileTimestamp {};'.format(datetime.datetime.now().strftime('%m-%d-%y %H:%M:%S')))
    add_klarf_content(klarf_file, f'InspectionStationID "ADC_DEMO" "PUMA9130" "{machine_name}";')
    add_klarf_content(klarf_file, 'SampleType WAFER;')
    add_klarf_content(klarf_file, 'ResultTimestamp {};'.format(
        (datetime.datetime.now() - datetime.timedelta(seconds=5)).strftime('%m-%d-%y %H:%M:%S')))
    add_klarf_content(klarf_file, 'LotID "{}";'.format(klarf_info['lot_id']))
    add_klarf_content(klarf_file, 'SampleSize 1 200;')
    add_klarf_content(klarf_file, 'DeviceID "{}";'.format(klarf_info['device_id']))
    add_klarf_content(klarf_file, 'SetupID "{}" {};'.format(klarf_info['setup_id'], (
            datetime.datetime.now() - datetime.timedelta(weeks=1)).strftime('%m-%d-%y %H:%M:%S')))
    add_klarf_content(klarf_file, 'StepID "{}";'.format(klarf_info['step_id']))
    add_klarf_content(klarf_file, 'SampleOrientationMarkType {};'.format(klarf_info['mark_type']))
    add_klarf_content(klarf_file, 'OrientationMarkLocation {};'.format(klarf_info['mark_location']))
    add_klarf_content(klarf_file,
                      'DiePitch {:.10E} {:.10E};'.format(klarf_info['die_pitch_width'], klarf_info['die_pitch_height']))
    add_klarf_content(klarf_file, 'DieOrigin {:.10E} {:.10E};'.format(-klarf_info['die_pitch_width'],
                                                                      -klarf_info['die_pitch_height']))
    add_klarf_content(klarf_file, 'WaferID "{}";'.format(klarf_info['wafer_id']))
    add_klarf_content(klarf_file, 'Slot {};'.format(klarf_info['slot']))
    add_klarf_content(klarf_file, 'ScribeID "{}";'.format(klarf_info['scribe_id']))
    add_klarf_content(klarf_file, f'TiffFileName {tiff_filename};')
    add_klarf_content(klarf_file,
                      'SampleCenterLocation {:.10E} {:.10E};'.format(klarf_info['center_x'], klarf_info['center_y']))


def generate_klarf_summary(klarf_file, testno, defects_per_test):
    """
    生成Klarf文件的Summary模块（动态按testno分组统计，完全匹配需求格式）
    :param klarf_file: Klarf内容列表（用于追加统计内容）
    :param testno: 测试分组总数（如2表示分2组，test=1和test=2）
    :param defects_per_test: 每组缺陷数量列表（如[100,100]，需与testno长度一致）
    """
    # 1. 写入SummarySpec（固定5个统计字段，与需求一致）
    add_klarf_content(klarf_file, 'SummarySpec 5')
    # 2. 写入字段说明行（缩进1个空格，结尾加";"，匹配需求格式）
    add_klarf_content(klarf_file, ' TESTNO NDEFECT DEFDENSITY NDIE NDEFDIE ;')
    # 3. 写入SummaryList标识
    add_klarf_content(klarf_file, 'SummaryList')

    # 4. 循环生成每组的统计行
    for test_idx in range(testno):
        current_test = test_idx + 1  # 测试编号（从1开始）
        current_defect_count = defects_per_test[test_idx]  # 当前组的缺陷数

        # 构建统计行（缩进1个空格，字段用空格分隔）
        summary_line = f' {current_test} {current_defect_count} 5.3340524435e-001 19525 123'

        # 最后一行统计需追加";"（符合Klarf格式规范）
        if current_test == testno:
            summary_line += ' ;'

        # 将统计行追加到Klarf内容中
        add_klarf_content(klarf_file, summary_line)


def generate_klarf_end(klarf_file):
    add_klarf_content(klarf_file, 'EndOfFile;')


def generate_class_lookup_table(klarf_file, defect_num_table):
    add_klarf_content(klarf_file, "ClassLookup {}".format(len(defect_num_table)))
    for k, v in defect_num_table.items():
        add_klarf_content(klarf_file, ' {} "{}"'.format(k, v))
    klarf_file[-1] = klarf_file[-1].decode().replace('\n', ' ;\n').encode()


def add_klarf_content(klarf_file, message):
    # tool_logger.INFO("add_klarf_content")
    klarf_file.append(bytes(message + "\n", encoding='utf8'))


def generate_defect_location(die_pitch_size, wafer_diameter):
    die_width = die_pitch_size[0]
    die_height = die_pitch_size[1]
    wafer_radius = wafer_diameter / 2
    loc_x = random.random() * wafer_diameter - wafer_radius
    loc_y = random.random() * wafer_diameter - wafer_radius
    while ((loc_x // die_width + 1) * die_width) ** 2 + (
            (loc_y // die_height + 1) * die_height) ** 2 > wafer_radius ** 2:
        loc_x = random.random() * wafer_diameter - wafer_radius
        loc_y = random.random() * wafer_diameter - wafer_radius
    return loc_x, loc_y


def generate_random_defect(defect_id, defect_class_number, die_pitch_size, wafer_diameter, image_count, current_test):
    """
    生成随机缺陷信息（新增current_test参数控制TEST字段）
    :param current_test: 当前缺陷所属的Test编号（1,2,...testno）
    """
    defect_x_size = round(random.uniform(10, 50), 3)
    defect_y_size = round(random.uniform(10, 50), 3)
    defect_d_size = max(defect_x_size, defect_y_size)
    loc_x, loc_y = generate_defect_location(die_pitch_size, wafer_diameter)
    x_index = math.ceil(loc_x / die_pitch_size[0])
    y_index = math.ceil(loc_y / die_pitch_size[1])
    x_rel = round(loc_x - (die_pitch_size[0] * (x_index - 1)), 3)
    y_rel = round(loc_y - (die_pitch_size[1] * (y_index - 1)), 3)
    defect_area = round(defect_x_size * defect_y_size, 3)
    # 缺陷类型映射（按需求仅601=a、602=b）
    defect_type = "a" if defect_class_number == 601 else "b"

    # 关键修改：TEST字段由current_test赋值，不再固定为1
    test = current_test
    cluster_number = 0
    fine_bin_number = 0
    review_sample = 1
    fa_class = 0
    sem_energy_density = 0.0
    sem_max_energy = 1
    sem_l1_sizeum = 0.0
    sem_l2_sizeumsq = 0.0
    sem_polarity = 0.0
    sem_defect_brightness = 0.0
    sem_reference_brightness = 0.0
    sem_is_array = 0
    sem_array_fractiion = 0.0
    sem_reference_complexity = 0.0
    sem_surface_index1 = 0.0
    sem_surface_index2 = 0.0
    distance_from_vertical_pagebreak = 0.0
    distance_from_horizontal_pagebreak = 0.0
    image_list = image_count

    defect_info = list()
    defect_info.extend([
        defect_id, x_rel, y_rel, x_index, y_index, defect_x_size, defect_y_size, defect_area, defect_d_size,
        defect_class_number, test, cluster_number, fine_bin_number, review_sample, fa_class, sem_energy_density,
        sem_max_energy, sem_l1_sizeum, sem_l2_sizeumsq, sem_polarity, sem_defect_brightness, sem_reference_brightness,
        sem_is_array, sem_array_fractiion, sem_reference_complexity, sem_surface_index1, sem_surface_index2,
        distance_from_vertical_pagebreak, distance_from_horizontal_pagebreak, image_count, image_list
    ])
    return defect_info

def count_write_klarf_file(klarf_file, klarf_filename):
    """
    将 klarf_file 中的内容写入到 klarf_filename 文件中，并返回操作结果。

    参数:
    klarf_file (iterable): 包含要写入内容的可迭代对象。
    klarf_filename (str): 要写入的文件名。

    返回:
    int: 如果写入成功，返回 1；如果写入失败，返回 0。
    """
    try:
        # 以二进制写模式打开文件
        with open(klarf_filename, 'wb') as f:
            # 遍历 klarf_file 中的每个元素，并写入文件
            for klarf in klarf_file:
                f.write(klarf)
        # 如果写入成功，返回 1
        return 1
    except Exception as e:
        # 如果写入过程中发生任何异常，打印异常信息并返回 0
        return 0


def load_templates(templates_dir='uploads'):
    """
    Load all template images from the specified directory and return them as a list.
    Handles resource paths correctly for both development and frozen (PyInstaller) environments.

    Args:
        templates_dir: Relative path to the templates directory (default: 'uploads')

    Returns:
        List of template images (numpy arrays), or None if directory doesn't exist
    """
    try:
        # Determine resource path base
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        # 在代码中添加调试信息

        # Construct full templates directory path
        full_templates_path = os.path.join(base_path, templates_dir)

        # Verify directory exists
        if not os.path.isdir(full_templates_path):
            print(f"警告: 模板目录不存在: {full_templates_path}")

            return None

        # Load all template images
        template_list = []
        supported_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff')

        for template_file in os.listdir(full_templates_path):
            if template_file.lower().endswith(supported_extensions):
                print()
                template_path = os.path.join(full_templates_path, template_file)
                template_img = cv2.imread(template_path)

                if template_img is not None:
                    template_list.append(template_img)
                else:
                    print(f"警告: 无法读取图像文件: {template_path}")

        return template_list if template_list else None

    except Exception as e:
        print(f"加载模板时发生错误: {str(e)}")
        return None


def is_valid_path_format(path):
    """
    检查输入是否是一个有效的路径格式。

    参数:
    path (str): 需要检查的路径。

    返回:
    bool: 如果路径格式有效，返回 True；否则返回 False。
    """
    if not isinstance(path, str):
        return False

    # 定义路径的正则表达式
    # 这个正则表达式匹配常见的路径格式，包括绝对路径和相对路径
    path_regex = re.compile(r'^(/|([a-zA-Z]:)?(\\|/))([\w.-]+(\\|/))*[\w.-]*$')

    # 检查路径是否符合正则表达式
    if not path_regex.match(path):
        return False

    return True


def count_write_tiff(tiff_path, tiff_data):
    """
    将 TIFF 数据写入指定路径，并返回写入状态。

    参数:
    tiff_path (str): TIFF 文件的路径。
    tiff_data (ndarray): 要写入的 TIFF 数据。

    返回:
    int: 如果写入成功，返回 1；如果写入失败，返回 0。
    """
    try:
        # 使用 tifffile 库将数据写入 TIFF 文件
        # append=True 表示追加写入，bigtiff=True 表示使用 BigTIFF 格式
        imwrite(tiff_path, tiff_data, append=True, bigtiff=True)
        return 1
    except Exception as e:
        # 记录错误信息
        return 0




