import os
import random
import sys
import threading
import time

import cv2
import numpy as np

from tools import count_write_klarf_file, generate_klarf_end, generate_klarf_summary, add_klarf_content, \
    count_write_tiff, generate_random_defect, generate_defect_image_group, get_reference, sampletestplan, \
    generate_class_lookup_table, generate_klarf_header,load_templates

class WaferScanner:
    def __init__(self):
        # 初始化类的必要属性（与scanned函数中用到的self.xxx对应）
        self.wafer_list = [1, 2, 3, 4, 5]  # 晶圆ID列表（你传入的参数）
        self.inspection_tool = '1212'       # 检测工具ID（你传入的参数）
        self.shot_size = 680               # 截图尺寸（你传入的参数）
        self.channel = 3                    # 图像通道数（AOI默认3通道RGB）
        self.machine_type = 'SEM'           # 机台类型（AOI/SEM，你传入的参数）
        self.mode = 'local'                 # 运行模式（本地/local，可按需改）
        self.interval = 0                   # 生成间隔时间（秒，0表示无间隔）
        self.machine_id = 'AOI_001'         # 机台ID（自定义，用于数据库记录）
        self.lock = threading.Lock()        # 线程锁（原代码用于数据库安全更新）
        # 数据库相关（若不需要数据库记录，可注释，但需删除scanned中db相关代码）
        # self.db = db

    # -------------------------- 2. 复制你原代码中的所有辅助函数（关键！） --------------------------
    # （包括：add_black_dot、add_blob、add_scratch、add_triangle、generate_defect_image、
    #  generate_alphabets、get_shot、generate_topograph、generate_material、center_zoom、
    #  generate_defect_image_group、turn_list、get_reference、generate_klarf_header、
    #  generate_klarf_summary、generate_klarf_end、generate_class_lookup_table、
    #  add_klarf_content、generate_defect_location、generate_random_defect、
    #  count_write_klarf_file、load_templates、is_valid_path_format、count_write_tiff）
    # 注意：需将之前修改后的 generate_random_defect、generate_klarf_summary 放入此处

    # （此处省略辅助函数代码，需你手动复制原代码中的所有辅助函数到此类中）
    def scanned(self, product_id, lot_id, step_id, defects, template, iteration, task_id, testno):
        """
        机台扫描（支持按testno分组缺陷）
        :param product_id: 产品名
        :param lot_id: 批次ID
        :param step_id: 层ID
        :param defects: 总缺陷数量
        :param template: 模板图片
        :param iteration: 迭代次数
        :param task_id: 任务id
        :param testno: 需分组的测试编号总数（如2表示分2组，test=1和test=2）
        :return:
        """
        import math  # 确保导入math模块
        path = f'chip_machine_data/{product_id}/{lot_id}/{step_id}'
        die_pitch_width = 1981.9980000
        die_pitch_height = 1381.0040000
        wafer_diameter = 300000
        klarf_info = dict()
        klarf_info['device_id'] = product_id
        klarf_info['lot_id'] = lot_id
        klarf_info['step_id'] = step_id
        klarf_info['setup_id'] = f'{product_id} {step_id}'
        klarf_info['mark_type'] = 'NOTCH'
        klarf_info['mark_location'] = 'DOWN'
        klarf_info['die_pitch_width'] = die_pitch_width
        klarf_info['die_pitch_height'] = die_pitch_height
        klarf_info['center_x'] = 0.0
        klarf_info['center_y'] = 0.0

        # 缺陷字段列表（保持不变）
        defect_properties = [
            'DEFECTID', 'XREL', 'YREL', 'XINDEX', 'YINDEX', 'XSIZE', 'YSIZE', 'DEFECTAREA', 'DSIZE', 'CLASSNUMBER',
            'TEST', 'CLUSTERNUMBER', 'FINEBINNUMBER', 'REVIEWSAMPLE', 'FACLASS', 'SEMENERGYDENSITY', 'SEMMAXENERGY',
            'SEML1SIZEUM', 'SEML2SIZEUMSQ', 'SEMPOLARITY', 'SEMDEFECTBRIGHTNESS', 'SEMREFERENCEBRIGHTNESS',
            'SEMISARRAY', 'SEMARRAYFRACTION', 'SEMREFERENCECOMPLEXITY', 'SEMSURFACEINDEX1', 'SEMSURFACEINDEX2',
            'DISTANCEFROMVERTICALPAGEBREAK', 'DISTANCEFROMHORIZONTALPAGEBREAK', 'IMAGECOUNT', 'IMAGELIST'
        ]

        # -------------------------- 1. 计算每组缺陷数量（按testno均分） --------------------------
        if testno <= 0:
            raise ValueError("testno（测试组数）必须大于0！")
            # 1. 计算每组“基础缺陷数”（总缺陷数 // 测试组数，前面组按此数量分配）
        base_defects_per_test = defects // testno  # 整除结果（如defects=201, testno=2 → base=100）
        # 2. 计算剩余缺陷数（总缺陷数 % 测试组数，全部给最后一组）
        remaining_defects = defects % testno  # 取余结果（如201%2=1，最后一组多1个）
        # 3. 生成每组缺陷数量列表（前面testno-1组按base分配，最后1组分base+remaining）
        defects_per_test = []
        for i in range(testno):
            if i < testno - 1:  # 前面testno-1组（如testno=2时，i=0是第1组）
                defects_per_test.append(base_defects_per_test)
            else:  # 最后1组（i=testno-1），承接剩余缺陷
                defects_per_test.append(base_defects_per_test + remaining_defects)
        # 4. 生成每组的缺陷ID范围（用于后续判断缺陷属于哪一组）
        test_defect_ranges = []
        current_start = 1
        for count in defects_per_test:
            current_end = current_start + count - 1
            test_defect_ranges.append((current_start, current_end))  # 如[(1,100), (101,201)]
            current_start = current_end + 1

        # -------------------------- 2. 遍历晶圆列表生成数据 --------------------------
        for wafer_id in self.wafer_list:
            s_g_time = time.time()
            tiff_filename = f'{lot_id}_{wafer_id}_{step_id}.tif'

            klarf_info['wafer_id'] = wafer_id
            klarf_info['slot'] = wafer_id
            klarf_info['scribe_id'] = f'{lot_id}_{wafer_id}'
            klarf_content = list()

            # 生成Klarf头部（不变）
            generate_klarf_header(klarf_content, klarf_info, self.inspection_tool, tiff_filename)
            # 生成缺陷分类表（按需求改为2类：601=a, 602=b）
            generate_class_lookup_table(klarf_content, {601: "a", 602: "b"})
            add_klarf_content(klarf_content, 'OrientationInstructions "";')

            # -------------------------- 3. 生成多Test模块（InspectionTest X + SampleTestPlan + AreaPerTest） --------------------------
            for test in range(1, testno + 1):
                add_klarf_content(klarf_content, f'InspectionTest {test};')
                add_klarf_content(klarf_content, sampletestplan)  # 复用原有SampleTestPlan配置

            # 生成缺陷记录规范（不变）
            add_klarf_content(
                klarf_content, 'DefectRecordSpec {} {} ;'.format(len(defect_properties), ' '.join(defect_properties))
            )
            add_klarf_content(klarf_content, 'DefectList')

            # 创建目录（不变）
            if not os.path.exists(f'{path}/{wafer_id}'):
                os.makedirs(f'{path}/{wafer_id}')

            # -------------------------- 4. 生成缺陷数据（按Test分组赋值TEST字段） --------------------------
            for defect_id in range(1, defects + 1):
                # 确定当前缺陷所属的Test编号（如defect_id=3 → test=1，defect_id=6 → test=2）
                current_test = None
                for test_idx, (start, end) in enumerate(test_defect_ranges):
                    if start <= defect_id <= end:
                        current_test = test_idx + 1  # test编号从1开始
                        break

                # 生成缺陷类型（保持原有逻辑，缺陷类别限定为601/602，与ClassLookup对应）
                defect_class_number = random.choice([601, 602])  # 按需求仅生成601/602两类缺陷
                reference = get_reference(template, (self.shot_size, self.shot_size))
                image_group = generate_defect_image_group(
                    reference, defect_class_number, self.machine_type, self.shot_size
                )
                image_count = len(image_group)

                # 生成缺陷信息（关键：传入current_test替换原固定test=1）
                defect_info = generate_random_defect(
                    defect_id, defect_class_number,
                    (die_pitch_width, die_pitch_height),
                    wafer_diameter, image_count,
                    current_test  # 新增参数：传递当前缺陷所属的Test编号
                )

                # 生成TIFF图片（保持原有逻辑）
                tiff_data = np.ndarray(shape=(image_count, self.channel, self.shot_size, self.shot_size), dtype=np.uint8)
                for i, img in enumerate(image_group):
                    if self.machine_type == 'AOI':
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)
                        tiff_data[i, ...] = img
                    elif self.machine_type == 'SEM':
                        tiff_data[i, 0, ...] = img
                if self.machine_type != 'Inspection':
                    tiff_path = f'{path}/{wafer_id}/{tiff_filename}'
                    count_write_tiff(tiff_path, tiff_data)

                # 写入缺陷记录到Klarf（保持原有逻辑）
                add_klarf_content(klarf_content, ' ' + ' '.join(str(item) for item in defect_info))
                if self.machine_type == 'AOI':
                    if defect_id == defects:
                        add_klarf_content(klarf_content, f'{defect_id} 0 ;')
                    else:
                        add_klarf_content(klarf_content, f'{defect_id} 0')
                elif self.machine_type == 'SEM':
                    for i in range((defect_id - 1) * 9 + 1, defect_id * 9 + 1):
                        if defect_id == defects and i == defect_id * 9:
                            add_klarf_content(klarf_content, f'{i} 0 ;')
                        else:
                            add_klarf_content(klarf_content, f'{i} 0')
                if defect_id % 100 == 0:
                    pass
            # -------------------------- 5. 生成动态SummaryList（按每组缺陷数统计） --------------------------
            generate_klarf_summary(klarf_content, testno, defects_per_test)  # 传递分组信息

            # 生成文件结尾（不变）
            generate_klarf_end(klarf_content)
            klarf_filename = '_'.join([lot_id, str(wafer_id), step_id]) + '.0'
            klarf_filename = f'{path}/{wafer_id}/{klarf_filename}'
            count_write_klarf_file(klarf_content, klarf_filename)

            # -------------------------- 6. 数据库记录与任务更新（保持原有逻辑） --------------------------
            # if self.mode == 'local':
            #     if self.machine_type != 'Inspection':
            #         pass  # 原有数据入湖逻辑可按需恢复
            #
            # test_result = TestResult(
            #     task_id=task_id,
            #     machine_success_files_total=2,
            #     machine_id=self.machine_id,
            #     iteration=iteration
            # )
            # db.session.add(test_result)
            # db.session.commit()
            #
            # # 速率控制
            # generation_time = time.time() - s_g_time
            # if self.interval:
            #     sleep_time = max(0, self.interval - generation_time)
            #     t.INFO(f"generation_time < self.interval，SLEEP {sleep_time} 秒" if generation_time < self.interval
            #            else f"generation_time > self.interval，SLEEP {sleep_time} 秒")
            #     time.sleep(sleep_time)
            # max_file_num = 3600 // generation_time * 2
            #
            # # 更新任务状态
            # try:
            #     with self.lock:
            #         task_info = db.session.query(TestTask).filter(TestTask.task_id == task_id).with_for_update().first()
            #         if task_info:
            #             should_generate = task_info.should_generate
            #             total_sum = db.session.query(db.func.sum(TestResult.machine_success_files_total)).filter(
            #                 TestResult.task_id == task_id).scalar() or 0
            #             if total_sum >= should_generate:
            #                 status = "completed"
            #                 progress = 100
            #             else:
            #                 status = "running"
            #                 progress = 100 * total_sum / should_generate if should_generate > 0 else 0
            #             task_info.status = status
            #             task_info.progress = progress
            #             if task_info.task_id.startswith('FUNC'):
            #                 task_info.end_time = datetime.now()
            #                 task_info.file_generation_speed = max_file_num
            #             db.session.commit()
            # except SQLAlchemyError as e:
            #     db.session.rollback()
            #     print(f"Error updating task {task_id}: {e}")

if __name__ == "__main__":
    # 初始化扫描类实例
    scanner = WaferScanner()

    # -------------------------- 加载模板图片 --------------------------
    # 调用load_templates加载uploads目录下的模板（返回模板列表，取第一张作为默认模板）
    template_list = load_templates(templates_dir='uploads')  # templates_dir默认是uploads，可改路径
    if not template_list:
        print("ERROR：未加载到任何模板图片！请检查uploads目录是否存在且有图片")
        sys.exit(1)  # 无模板则退出，避免后续报错
    # 取第一张模板作为传入scanned的template参数（多模板可循环取，此处简化用第一张）
    template = template_list[0]

    # -------------------------- 定义scanned函数的其他参数 --------------------------
    product_id = 'adc_adc'       # 产品名（自定义）
    lot_id = 'dsad'              # 批次ID（自定义）
    step_id = 'STEP_1'           # 层ID（自定义）
    defects = 183              # 总缺陷数量（你传入的200）
    iteration = 1                # 迭代次数（自定义，用于记录第几次生成）
    task_id = 'TASK_20250827_001'# 任务ID（自定义，用于数据库记录）
    testno = 5                  # 按testno分组数量（如2表示分2组，test=1和test=2）

    # -------------------------- 调用scanned函数生成数据 --------------------------
    print(f"开始生成：产品{product_id}，批次{lot_id}，层{step_id}，总缺陷{defects}，分{testno}组")
    scanner.scanned(
        product_id=product_id,
        lot_id=lot_id,
        step_id=step_id,
        defects=defects,
        template=template,  # 传入加载好的模板图片
        iteration=iteration,
        task_id=task_id,
        testno=testno       # 传入分组数量（关键参数）
    )
    print("生成完成！数据保存路径：chip_machine_data/{product_id}/{lot_id}/{step_id}")