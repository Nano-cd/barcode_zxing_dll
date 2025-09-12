import cv2
import numpy as np


class BarcodeQualityAssessor1D:
    """
    仿照 ISO/IEC 15416 标准，为预先裁剪好的一维（线性）条码进行质量评估。
    此版本经过重构，支持自定义评分阈值，并区分“分数”与“等级”，最后根据平均分数进行综合评估。
    """
    GRADE_MAP_NUM = {'A': 4, 'B': 3, 'C': 2, 'D': 1, 'F': 0}

    # 默认阈值，仿照 ISO 标准。可以被外部传入的字典覆盖。
    DEFAULT_THRESHOLDS = {
        'Symbol Contrast': {'values': [0.7 * 255, 0.55 * 255, 0.40 * 255, 0.20 * 255], 'lower_is_better': False},
        'Modulation': {'values': [0.7, 0.6, 0.5, 0.4], 'lower_is_better': False},
        'Defect': {'values': [0.15, 0.20, 0.25, 0.30], 'lower_is_better': True},
        # Rmin Pass 是一个特例，它只有通过/不通过，我们用分数1/0表示
        'Rmin Pass': {'values': [0.5], 'lower_is_better': True}  # 实际上是 rmin/rmax <= 0.5, 所以是 lower is better
    }

    def __init__(self, image, thresholds=None):
        if image is None:
            raise ValueError("输入图像不能为空。")
        self.image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # 如果未提供自定义阈值，则使用默认值
        self.thresholds = thresholds if thresholds is not None else self.DEFAULT_THRESHOLDS

        self.results = {}
        self.scan_y_indices = []

    def _get_grade_from_score(self, parameter_name, score):
        """根据分数和配置的阈值为指定参数评级。"""
        if parameter_name not in self.thresholds:
            return 'N/A'

        config = self.thresholds[parameter_name]
        thresholds = config['values']
        lower_is_better = config['lower_is_better']

        # 特殊处理 Rmin Pass
        if parameter_name == 'Rmin Pass':
            return 'A' if score == 1 else 'F'

        if lower_is_better:
            if score <= thresholds[0]: return 'A'
            if score <= thresholds[1]: return 'B'
            if score <= thresholds[2]: return 'C'
            if score <= thresholds[3]: return 'D'
            return 'F'
        else:
            if score >= thresholds[0]: return 'A'
            if score >= thresholds[1]: return 'B'
            if score >= thresholds[2]: return 'C'
            if score >= thresholds[3]: return 'D'
            return 'F'

    def _get_scan_profiles(self, num_scans=10):
        """在条码高度上均匀获取多条扫描剖面（像素行）。"""
        h, w = self.image.shape
        self.scan_y_indices = np.linspace(0, h - 1, num_scans, dtype=int)
        profiles = [self.image[y, :] for y in self.scan_y_indices]
        return profiles

    def _analyze_single_profile(self, profile):
        """
        对单条扫描剖面进行分析，返回每个参数的原始分数。
        """
        analysis_scores = {}

        # 预设失败情况下的分数
        fail_scores = {'Symbol Contrast': 0, 'Modulation': 0, 'Defect': 1.0, 'Rmin Pass': 0}

        # 检查 profile 是否有效
        if np.max(profile) == np.min(profile):
            return fail_scores

        rmin, rmax = np.min(profile), np.max(profile)

        # Rmin Pass (分数: 1表示通过, 0表示失败)
        analysis_scores['Rmin Pass'] = 1 if rmin < 0.5 * rmax else 0

        # Symbol Contrast (分数: rmax - rmin)
        sc = rmax - rmin
        analysis_scores['Symbol Contrast'] = sc

        if sc == 0:
            return fail_scores

        global_threshold = rmin + sc / 2.0
        edges = np.where(np.diff(profile > global_threshold))[0]

        if len(edges) < 2:
            return fail_scores

        # --- 提取元素信息 ---
        elements_max, elements_min, elements_mean = [], [], []
        for i in range(len(edges) - 1):
            # 一个元素的范围是从一个边缘之后，到下一个边缘（包含）
            start_pixel_idx = edges[i] + 1
            end_pixel_idx = edges[i + 1] + 1  # +1 是因为python切片不包含末尾

            # 安全检查，防止索引越界
            if start_pixel_idx >= end_pixel_idx or end_pixel_idx > len(profile):
                continue

            segment = profile[start_pixel_idx:end_pixel_idx]

            if segment.size > 0:
                elements_max.append(np.max(segment))
                elements_min.append(np.min(segment))
                elements_mean.append(np.mean(segment))

        if len(elements_mean) < 2:
            return fail_scores

        # --- Modulation (分数: ec_min / sc) ---
        ec_min = sc
        for i in range(len(elements_mean) - 1):
            edge_contrast = abs(elements_mean[i] - elements_mean[i + 1])
            if edge_contrast < ec_min:
                ec_min = edge_contrast
        mod = ec_min / sc
        analysis_scores['Modulation'] = mod

        # --- Defect (分数: max(element_contrast / sc)) ---
        max_defect = 0
        for i in range(len(elements_min)):
            internal_contrast = elements_max[i] - elements_min[i]
            local_defect = internal_contrast / sc
            if local_defect > max_defect:
                max_defect = local_defect
        analysis_scores['Defect'] = max_defect

        return analysis_scores

    def evaluate(self):
        """
        执行评估流程：逐行分析、汇总平均、最终评级。
        """
        print("--- 开始条码质量评估 ---")

        print("\n步骤 1: 获取10条扫描剖面...")
        profiles = self._get_scan_profiles(num_scans=10)

        # 我们只分析中间的8条线
        profiles_to_analyze = profiles[1:-1]
        y_indices_to_analyze = self.scan_y_indices[1:-1]
        if len(profiles_to_analyze) == 0:
            raise RuntimeError("图像高度太小，无法进行有效扫描。")

        print(f"步骤 2: 逐条分析中间的 {len(profiles_to_analyze)} 条扫描剖面，计算各项分数...")

        scan_reports = []
        # 用于存储所有扫描线分数的列表
        all_scores = {param: [] for param in self.DEFAULT_THRESHOLDS.keys()}

        for i, profile in enumerate(profiles_to_analyze):
            scan_number = i + 1
            scores = self._analyze_single_profile(profile)

            # 为每个分数计算对应的等级
            grades = {param: self._get_grade_from_score(param, score) for param, score in scores.items()}

            # 存储每条线的详细报告
            report = {
                'scan_number': scan_number,
                'y_coordinate': y_indices_to_analyze[i],
                'scores': scores,
                'grades': grades
            }
            scan_reports.append(report)

            # 收集分数用于后续平均
            for param, score in scores.items():
                all_scores[param].append(score)

            print(f"  扫描线 #{scan_number} (Y={report['y_coordinate']}): "
                  f"SC={scores['Symbol Contrast']:.1f}({grades['Symbol Contrast']}), "
                  f"MOD={scores['Modulation']:.2f}({grades['Modulation']}), "
                  f"DEF={scores['Defect']:.2f}({grades['Defect']}), "
                  f"Rmin={scores['Rmin Pass']}({grades['Rmin Pass']})")

        self.results['Scan Reports'] = scan_reports

        print("\n步骤 3: 计算平均分数并确定综合等级...")
        overall_summary = {}
        overall_grades = []

        for param, scores_list in all_scores.items():
            if scores_list:
                avg_score = np.mean(scores_list)
                # 根据平均分评定综合等级
                grade = self._get_grade_from_score(param, avg_score)
                overall_summary[param] = {'average_score': avg_score, 'grade': grade}
                overall_grades.append(grade)
                print(f"  参数 '{param}': 平均分 = {avg_score:.3f}, 综合等级 = {grade}")
            else:
                overall_summary[param] = {'average_score': float('nan'), 'grade': 'F'}
                overall_grades.append('F')

        self.results['Overall Summary'] = overall_summary

        # 条码的总等级由所有参数的综合等级中最差的一个决定
        if overall_grades:
            final_grade = min(overall_grades, key=lambda g: self.GRADE_MAP_NUM.get(g, -1))
            self.results['Overall Grade'] = final_grade
        else:
            self.results['Overall Grade'] = 'F'

        print(f"\n--- 评估完成 --- \n最终综合等级: {self.results['Overall Grade']}")

        return self.results

    def visualize_results(self):
        """
        创建包含详细分数和等级的可视化结果图像。
        """
        vis_img = cv2.cvtColor(self.image, cv2.COLOR_GRAY2BGR)
        h, w, _ = vis_img.shape

        # 绘制扫描线
        for i, y in enumerate(self.scan_y_indices):
            color = (0, 255, 255) if 1 <= i < 9 else (0, 0, 255)
            cv2.line(vis_img, (0, y), (w, y), color, 1)
            if 1 <= i < 9:
                cv2.putText(vis_img, str(i), (5, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)

        # --- 创建详细报告视图 ---
        report_width = 450
        report_canvas = np.full((max(h, 500), report_width, 3), 255, dtype=np.uint8)
        font = cv2.FONT_HERSHEY_SIMPLEX  # 使用等宽字体以对齐

        # 标题和总评级
        cv2.putText(report_canvas, "Barcode Quality Report", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        overall_grade = self.results.get('Overall Grade', 'N/A')
        grade_color = (0, 128, 0) if overall_grade in ['A', 'B'] else (0, 0, 255)
        cv2.putText(report_canvas, f"Overall: {overall_grade}", (report_width - 150, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, grade_color, 2)
        cv2.line(report_canvas, (10, 40), (report_width - 10, 40), (0, 0, 0), 1)

        # --- 逐行报告 ---
        y_pos = 65
        line_height = 20
        header = f"{'Scan':<5}{'SC (Grade)':<12}{'MOD (Grade)':<12}{'DEF (Grade)':<12}"
        cv2.putText(report_canvas, header, (10, y_pos), font, 0.4, (0, 0, 0), 1)
        y_pos += line_height

        if 'Scan Reports' in self.results:
            for report in self.results['Scan Reports']:
                s, g = report['scores'], report['grades']
                sc_str = f"{s['Symbol Contrast']:.0f}({g['Symbol Contrast']})"
                mod_str = f"{s['Modulation']:.2f}({g['Modulation']})"
                def_str = f"{s['Defect']:.2f}({g['Defect']})"

                line_text = f"{report['scan_number']:<5}{sc_str:<12}{mod_str:<12}{def_str:<12}"
                color = (0, 100, 0)
                if any(gr in ['C', 'D', 'F'] for gr in g.values()):
                    color = (0, 0, 255)

                cv2.putText(report_canvas, line_text, (10, y_pos), font, 0.4, color, 1)
                y_pos += line_height

        y_pos += line_height  # 添加一些间距

        # --- 综合评估报告 ---
        cv2.line(report_canvas, (10, y_pos), (report_width - 10, y_pos), (0, 0, 0), 1)
        y_pos += line_height
        cv2.putText(report_canvas, "Overall Summary (based on average scores)", (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 0, 0), 1)
        y_pos += line_height + 5

        summary_header = f"{'Parameter':<18}{'Avg Score':<12}{'Grade':<6}"
        cv2.putText(report_canvas, summary_header, (10, y_pos), font, 0.5, (0, 0, 0), 1)
        y_pos += line_height

        if 'Overall Summary' in self.results:
            summary = self.results['Overall Summary']
            for param, data in summary.items():
                score_str = f"{data['average_score']:.3f}"
                grade_str = data['grade']
                line_text = f"{param:<18}{score_str:<12}{grade_str:<6}"

                color = (0, 128, 0) if grade_str in ['A', 'B'] else (0, 0, 255)
                cv2.putText(report_canvas, line_text, (10, y_pos), font, 0.5, color, 1)
                y_pos += line_height

        # 拼接图像
        if vis_img.shape[0] < report_canvas.shape[0]:
            padding = np.zeros((report_canvas.shape[0] - vis_img.shape[0], vis_img.shape[1], 3), dtype=np.uint8)
            vis_img = np.vstack((vis_img, padding))
        elif report_canvas.shape[0] < vis_img.shape[0]:
            padding = np.full((vis_img.shape[0] - report_canvas.shape[0], report_canvas.shape[1], 3), 255,
                              dtype=np.uint8)
            report_canvas = np.vstack((report_canvas, padding))

        final_view = np.hstack((vis_img, report_canvas))
        return final_view


if __name__ == '__main__':
    # 示例用法
    # 请将 'path/to/your/barcode.jpg' 替换为你的条码图片路径
    file_path = 'E:/project_pycharm/MYMLOPs/barcode/output_images/area_0/240903091030-16-1_class_0_0001.jpg'
    barcode_image = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)

    # --- 示例1: 使用默认 (类ISO) 阈值 ---
    print("====== 评估 1: 使用默认阈值 ======")
    assessor_default = BarcodeQualityAssessor1D(barcode_image)
    results_default = assessor_default.evaluate()

    # 可视化结果
    vis_default = assessor_default.visualize_results()
    cv2.imshow("results", vis_default)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
