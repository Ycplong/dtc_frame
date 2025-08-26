"""config_key	varchar	配置键（唯一）	testno_switch
config_value	tinyint	配置值（1 = 开启，0 = 关闭）	1
config_desc	varchar	配置描述	"是否启用 testno 分组逻辑"""


"""字段名	类型	说明	示例值
machine_id	varchar	机台 ID（与 self.machine_id 一致）	AOI_001
testno	int	该机台的 testno 分组数	2
wafer_id_list	varchar	该机台的晶圆 ID 列表（逗号分隔）	"1,2,3,4,5"
is_valid	tinyint	配置是否有效	1"""





def scanned(self, product_id, lot_id, step_id, defects, template, iteration, task_id):
    """
    机台扫描（新增：基于数据库全局开关+机台testno动态控制分组逻辑）
    :param product_id: 产品名
    :param lot_id: 批次ID
    :param step_id: 层ID
    :param defects: 总缺陷数量
    :param template: 模板图片
    :param iteration: 迭代次数
    :param task_id: 任务ID
    :return:
    """
    import math
    from sqlalchemy.exc import SQLAlchemyError  # 导入数据库异常处理
    # -------------------------- 1. 数据库查询：全局开关+机台testno --------------------------
    # 初始化默认值（开关关闭：不分组，testno=1，使用原wafer_list）
    use_testno_logic = False  # 是否启用testno分组逻辑
    current_testno = 1        # 默认不分组（仅1组）
    current_wafer_list = self.wafer_list  # 默认使用类初始化的wafer_list

    try:
        # 加锁确保数据库查询安全（避免并发冲突）
        with self.lock:
            # 1.1 查询全局开关：是否启用testno分组
            # global_switch = db.session.query(global_config.config_value)\
            #     .filter(global_config.config_key == "testno_switch", global_config.is_valid == 1)\
            #     .scalar()  # 返回1/0或None
            global_switch = 0
            if global_switch == 1:  # 全局开关开启
                use_testno_logic = True
                # 1.2 查询当前机台的专属配置（machine_id与self.machine_id匹配）
                machine_config = db.session.query(machine_config.testno, machine_config.wafer_id_list)\
                    .filter(machine_config.machine_id == self.machine_id, machine_config.is_valid == 1)\
                    .first()  # 返回tuple：(testno, wafer_id_list)或None

                if machine_config:
                    # 1.2.1 获取机台专属testno（需>0，否则用默认1）
                    current_testno = machine_config.testno if machine_config.testno > 0 else 1
                    # 1.2.2 获取机台专属wafer_id_list（逗号分隔转列表，空则用默认）
                    if machine_config.wafer_id_list and machine_config.wafer_id_list.strip():
                        current_wafer_list = [int(wid.strip()) for wid in machine_config.wafer_id_list.split(",")]
                        # 去重+排序（避免异常数据）
                        current_wafer_list = sorted(list(set(current_wafer_list)))
                else:
                    # 机台无配置：用默认testno=1+默认wafer_list
                    current_testno = 1
                    current_wafer_list = self.wafer_list
                    t.WARNING(f"机台{self.machine_id}无有效配置，使用默认逻辑（不分组）")
            else:
                # 全局开关关闭：用默认逻辑
                t.INFO("全局testno开关未开启，使用默认逻辑（不分组）")

    except SQLAlchemyError as e:
        # 数据库查询异常：降级为默认逻辑，避免函数崩溃
        db.session.rollback()
        t.ERROR(f"查询数据库配置失败：{str(e)}，降级为默认逻辑（不分组）")
        use_testno_logic = False
        current_testno = 1
        current_wafer_list = self.wafer_list

    # -------------------------- 2. 初始化基础参数（不变） --------------------------
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

    defect_properties = [
        'DEFECTID', 'XREL', 'YREL', 'XINDEX', 'YINDEX', 'XSIZE', 'YSIZE', 'DEFECTAREA', 'DSIZE', 'CLASSNUMBER',
        'TEST', 'CLUSTERNUMBER', 'FINEBINNUMBER', 'REVIEWSAMPLE', 'FACLASS', 'SEMENERGYDENSITY', 'SEMMAXENERGY',
        'SEML1SIZEUM', 'SEML2SIZEUMSQ', 'SEMPOLARITY', 'SEMDEFECTBRIGHTNESS', 'SEMREFERENCEBRIGHTNESS',
        'SEMISARRAY', 'SEMARRAYFRACTION', 'SEMREFERENCECOMPLEXITY', 'SEMSURFACEINDEX1', 'SEMSURFACEINDEX2',
        'DISTANCEFROMVERTICALPAGEBREAK', 'DISTANCEFROMHORIZONTALPAGEBREAK', 'IMAGECOUNT', 'IMAGELIST'
    ]

    # -------------------------- 3. 根据开关状态生成缺陷分组逻辑 --------------------------
    if use_testno_logic:
        t.INFO(f"启用testno分组逻辑：机台{self.machine_id}，testno={current_testno}，晶圆列表={current_wafer_list}")
        # 3.1 计算每组缺陷数量（前面组满配，最后组分剩余）
        base_defects_per_test = defects // current_testno
        remaining_defects = defects % current_testno
        defects_per_test = []
        for i in range(current_testno):
            if i < current_testno - 1:
                defects_per_test.append(base_defects_per_test)
            else:
                defects_per_test.append(base_defects_per_test + remaining_defects)
        # 3.2 生成每组缺陷ID范围（用于匹配缺陷所属test）
        test_defect_ranges = []
        current_start = 1
        for count in defects_per_test:
            current_end = current_start + count - 1
            test_defect_ranges.append((current_start, current_end))
            current_start = current_end + 1
    else:
        t.INFO("使用默认逻辑（不分组）：所有缺陷归为test=1")
        # 3.3 不分组：仅1组，所有缺陷属test=1
        current_testno = 1
        defects_per_test = [defects]
        test_defect_ranges = [(1, defects)]

    # -------------------------- 4. 遍历晶圆列表生成数据（用current_wafer_list替代self.wafer_list） --------------------------
    for wafer_id in current_wafer_list:  # 关键：使用机台专属晶圆列表
        s_g_time = time.time()
        tiff_filename = f'{lot_id}_{wafer_id}_{step_id}.tif'
        t.INFO(f"当前执行模拟制造晶圆id:{wafer_id}的数据")
        klarf_info['wafer_id'] = wafer_id
        klarf_info['slot'] = wafer_id
        klarf_info['scribe_id'] = f'{lot_id}_{wafer_id}'
        klarf_content = list()

        # 生成Klarf头部（不变）
        generate_klarf_header(klarf_content, klarf_info, self.inspection_tool, tiff_filename)
        # 生成缺陷分类表（按需求：601="a"，602="b"）
        generate_class_lookup_table(klarf_content, {601: "a", 602: "b"})
        add_klarf_content(klarf_content, 'OrientationInstructions "";')

        # -------------------------- 5. 按testno生成多Test模块（开关开启时） --------------------------
        if use_testno_logic:
            # 生成多个InspectionTest（1到current_testno）
            for test in range(1, current_testno + 1):
                add_klarf_content(klarf_content, f'InspectionTest {test};')
                add_klarf_content(klarf_content, sampletestplan)  # 复用SampleTestPlan
        else:
            # 开关关闭：仅生成1个InspectionTest
            add_klarf_content(klarf_content, 'InspectionTest 1;')
            add_klarf_content(klarf_content, sampletestplan)

        # 生成缺陷记录规范（不变）
        add_klarf_content(
            klarf_content, 'DefectRecordSpec {} {} ;'.format(len(defect_properties), ' '.join(defect_properties))
        )
        add_klarf_content(klarf_content, 'DefectList')

        # 创建目录（不变）
        if not os.path.exists(f'{path}/{wafer_id}'):
            os.makedirs(f'{path}/{wafer_id}')

        # -------------------------- 6. 生成缺陷数据（按开关状态分配TEST字段） --------------------------
        for defect_id in range(1, defects + 1):
            # 6.1 确定当前缺陷所属的Test编号（开关开启则按分组，关闭则固定为1）
            current_test = 1  # 默认test=1
            if use_testno_logic:
                # 按test_defect_ranges匹配当前缺陷的test
                for test_idx, (start, end) in enumerate(test_defect_ranges):
                    if start <= defect_id <= end:
                        current_test = test_idx + 1
                        break

            # 6.2 生成缺陷类型（601/602，符合需求）
            defect_class_number = random.choice([601, 602])
            reference = get_reference(template, (self.shot_size, self.shot_size))
            image_group = generate_defect_image_group(
                reference, defect_class_number, self.machine_type, self.shot_size
            )
            image_count = len(image_group)

            # 6.3 生成缺陷信息（传入current_test）
            defect_info = generate_random_defect(
                defect_id, defect_class_number,
                (die_pitch_width, die_pitch_height),
                wafer_diameter, image_count,
                current_test  # 关键：按开关状态动态赋值test
            )

            # 6.4 生成TIFF图片（不变）
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

            # 6.5 写入缺陷记录（不变）
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
                t.INFO(f"CURRENT DEFECT:{defect_id}")

        # -------------------------- 7. 生成Summary（按开关状态动态统计） --------------------------
        generate_klarf_summary(klarf_content, current_testno, defects_per_test)

        # 生成文件结尾+写入文件（不变）
        generate_klarf_end(klarf_content)
        klarf_filename = '_'.join([lot_id, str(wafer_id), step_id]) + '.0'
        klarf_filename = f'{path}/{wafer_id}/{klarf_filename}'
        count_write_klarf_file(klarf_content, klarf_filename)

        # -------------------------- 8. 数据库记录与任务更新（不变） --------------------------
        if self.mode == 'local' and self.machine_type != 'Inspection':
            pass  # 数据入湖逻辑（按需恢复）

        try:
            test_result = TestResult(
                task_id=task_id,
                machine_success_files_total=2,
                machine_id=self.machine_id,
                iteration=iteration
            )
            db.session.add(test_result)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            t.ERROR(f"写入测试结果失败：{str(e)}")

        # 速率控制（不变）
        generation_time = time.time() - s_g_time
        if self.interval:
            sleep_time = max(0, self.interval - generation_time)
            t.INFO(f"生成耗时{generation_time:.2f}秒，休眠{sleep_time:.2f}秒")
            time.sleep(sleep_time)

        # 更新任务进度（不变）
        try:
            with self.lock:
                task_info = db.session.query(TestTask).filter(TestTask.task_id == task_id).with_for_update().first()
                if task_info:
                    should_generate = task_info.should_generate
                    total_sum = db.session.query(db.func.sum(TestResult.machine_success_files_total)).filter(
                        TestResult.task_id == task_id).scalar() or 0
                    task_info.status = "completed" if total_sum >= should_generate else "running"
                    task_info.progress = 100 * total_sum / should_generate if should_generate > 0 else 0
                    if task_info.task_id.startswith('FUNC'):
                        task_info.end_time = datetime.now()
                        task_info.file_generation_speed = 3600 // generation_time * 2 if generation_time > 0 else 0
                    db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            t.ERROR(f"更新任务{task_id}失败：{str(e)}")