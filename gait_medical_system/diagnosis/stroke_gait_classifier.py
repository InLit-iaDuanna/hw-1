"""
脑卒中步态模式分类器
基于V01-V24仿真研究成果的健康基准进行异常检测
"""

import numpy as np
from typing import Dict, List, Tuple


class StrokeGaitClassifier:
    """
    脑卒中步态分类和诊断建议生成器

    基于健康步态基准（V10/V13.7/V11）识别典型异常模式
    """

    def __init__(self, baseline_config=None):
        """
        Parameters:
        -----------
        baseline_config : dict, optional
            健康步态基准配置（默认使用baseline_extractor.py的输出）
        """
        if baseline_config is None:
            # 使用V10/V13.7默认基准
            self.baseline = self._load_default_baseline()
        else:
            self.baseline = baseline_config

        # 定义诊断规则权重
        self.rule_weights = {
            "asymmetry": 0.35,
            "rom_limitation": 0.25,
            "cadence_deviation": 0.15,
            "energy_efficiency": 0.15,
            "stability": 0.10,
        }

    def _load_default_baseline(self):
        """加载默认健康基准（与baseline_extractor.py一致）"""
        return {
            "stride_length": 1.05,
            "cadence": 60,
            "knee_rom": 60,
            "hip_rom": 40,
            "symmetry_threshold": 10,  # %
        }

    def classify_gait_pattern(self, patient_features: Dict) -> Dict:
        """
        分类步态模式

        Parameters:
        -----------
        patient_features : dict
            患者步态特征，包含:
            - stride_length_left, stride_length_right
            - cadence
            - knee_rom_left, knee_rom_right
            - hip_rom_left, hip_rom_right
            - cop_trajectory (optional)

        Returns:
        --------
        dict : 诊断结果
            - pattern_type: str (hemiplegic/circumduction/foot_drop/stiff_knee/normal)
            - severity_score: float (0-100)
            - affected_side: str (left/right/bilateral)
            - confidence: float (0-1)
        """
        diagnosis = {
            "pattern_type": "unknown",
            "severity_score": 0,
            "affected_side": "unknown",
            "confidence": 0.0,
            "features": {},
        }

        # 1. 计算对称性指数
        asymmetry = self._calculate_asymmetry(patient_features)
        diagnosis["features"]["asymmetry"] = asymmetry

        # 2. 识别步态模式
        if asymmetry["stride_length"] > 30:
            diagnosis["pattern_type"] = "hemiplegic_gait"
            diagnosis["severity_score"] = min(asymmetry["stride_length"] * 2, 100)
            diagnosis["affected_side"] = asymmetry["affected_side"]
            diagnosis["confidence"] = 0.9

        elif asymmetry["stride_length"] > 20:
            diagnosis["pattern_type"] = "mild_hemiplegic_gait"
            diagnosis["severity_score"] = asymmetry["stride_length"] * 1.5
            diagnosis["affected_side"] = asymmetry["affected_side"]
            diagnosis["confidence"] = 0.75

        # 3. 检测特定异常
        if "knee_rom_left" in patient_features and "knee_rom_right" in patient_features:
            knee_issues = self._detect_knee_issues(patient_features)
            if knee_issues["has_issue"]:
                diagnosis["features"]["knee_pathology"] = knee_issues
                if diagnosis["pattern_type"] == "unknown":
                    diagnosis["pattern_type"] = knee_issues["type"]
                    diagnosis["severity_score"] = knee_issues["severity"]

        # 4. 步频异常
        if "cadence" in patient_features:
            cadence_dev = (
                (patient_features["cadence"] - self.baseline["cadence"])
                / self.baseline["cadence"]
                * 100
            )
            diagnosis["features"]["cadence_deviation"] = cadence_dev

            if cadence_dev < -20:
                diagnosis["features"]["slow_walking"] = True
                diagnosis["severity_score"] += 15

        return diagnosis

    def _calculate_asymmetry(self, features: Dict) -> Dict:
        """
        计算步态对称性指数（Robinson Symmetry Index）

        SI = |X_left - X_right| / (0.5 * (X_left + X_right)) * 100

        基于V10双腿对称步态作为基准
        """
        asymmetry = {}

        # 步长不对称
        if "stride_length_left" in features and "stride_length_right" in features:
            left = features["stride_length_left"]
            right = features["stride_length_right"]

            si = abs(left - right) / (0.5 * (left + right)) * 100
            asymmetry["stride_length"] = si
            asymmetry["affected_side"] = "left" if left < right else "right"
            asymmetry["shorter_side_value"] = min(left, right)
            asymmetry["longer_side_value"] = max(left, right)

        # 步态时间不对称
        if "stance_time_left" in features and "stance_time_right" in features:
            left = features["stance_time_left"]
            right = features["stance_time_right"]
            asymmetry["stance_time"] = abs(left - right) / (0.5 * (left + right)) * 100

        return asymmetry

    def _detect_knee_issues(self, features: Dict) -> Dict:
        """检测膝关节相关问题"""
        knee_left = features.get("knee_rom_left", self.baseline["knee_rom"])
        knee_right = features.get("knee_rom_right", self.baseline["knee_rom"])
        baseline_knee = self.baseline["knee_rom"]

        knee_issues = {"has_issue": False, "type": "normal", "severity": 0}

        # 膝关节屈曲受限
        if min(knee_left, knee_right) < baseline_knee * 0.7:  # <42°
            knee_issues["has_issue"] = True
            knee_issues["type"] = "knee_flexion_limitation"
            knee_issues["severity"] = (
                1 - min(knee_left, knee_right) / baseline_knee
            ) * 100

        # 膝过伸
        if max(knee_left, knee_right) > baseline_knee * 1.2:  # >72°
            knee_issues["has_issue"] = True
            knee_issues["type"] = "knee_hyperextension"
            knee_issues["severity"] = (
                max(knee_left, knee_right) / baseline_knee - 1
            ) * 100

        return knee_issues

    def generate_recommendations(self, diagnosis: Dict) -> List[str]:
        """
        根据诊断结果生成康复建议

        基于V11鲁棒性边界和V13.7能量效率目标
        """
        recommendations = []
        pattern = diagnosis["pattern_type"]
        severity = diagnosis["severity_score"]

        # 偏瘫步态建议
        if "hemiplegic" in pattern:
            if severity > 50:
                recommendations.append(
                    "严重偏瘫步态：建议每日进行患侧下肢肌力强化训练（2组×15次）"
                )
                recommendations.append(
                    "使用体重支持跑台训练，逐步增加负重比例（从30%开始）"
                )
            else:
                recommendations.append(
                    "中度偏瘫步态：增加患侧负重训练，每日站立平衡练习15分钟"
                )

            # 对称性改善目标（基于V10对称步态）
            asymmetry = diagnosis["features"].get("asymmetry", {})
            if "stride_length" in asymmetry:
                current_si = asymmetry["stride_length"]
                target_si = 10  # V10基准：对称性指数<10%为正常
                recommendations.append(
                    f"对称性改善目标：当前{current_si:.1f}% → 目标<{target_si}%"
                )

        # 膝关节问题建议
        if "knee_pathology" in diagnosis["features"]:
            knee_issue = diagnosis["features"]["knee_pathology"]
            if knee_issue["type"] == "knee_flexion_limitation":
                recommendations.append(
                    "膝关节屈曲受限：进行被动/主动ROM训练，目标达到60°（V10基准）"
                )
            elif knee_issue["type"] == "knee_hyperextension":
                recommendations.append(
                    "膝过伸：加强股四头肌离心控制训练，考虑使用膝关节矫形器"
                )

        # 步行速度改善（基于V13.7能量效率）
        if "cadence_deviation" in diagnosis["features"]:
            if diagnosis["features"]["cadence_deviation"] < -20:
                recommendations.append(
                    "步行速度明显下降：渐进式增加步行速度训练，使用节拍器辅助（目标60步/分）"
                )
                recommendations.append(
                    "能量效率优化：参考V13.7准被动步态，减少不必要的代偿动作"
                )

        # 如果没有明显异常
        if not recommendations:
            recommendations.append(
                "步态参数接近健康基准（V10准被动步态），继续保持当前康复训练"
            )

        return recommendations

    def assess_fall_risk(self, patient_features: Dict) -> Dict:
        """
        评估跌倒风险

        基于V11鲁棒性边界：
        - 地形容差: 28.6 mm
        - 扰动容差: 17.1 N
        """
        risk_score = 0
        risk_factors = []

        # 对称性差 → 高跌倒风险
        if (
            "stride_length_left" in patient_features
            and "stride_length_right" in patient_features
        ):
            asymmetry = self._calculate_asymmetry(patient_features)
            if asymmetry.get("stride_length", 0) > 30:
                risk_score += 40
                risk_factors.append("severe_asymmetry")

        # 步频过慢 → 不稳定
        if patient_features.get("cadence", 100) < 50:
            risk_score += 20
            risk_factors.append("slow_cadence")

        # 关节活动度受限 → 无法应对扰动
        if patient_features.get("knee_rom_left", 60) < 40:
            risk_score += 15
            risk_factors.append("limited_knee_rom")

        # 评级
        if risk_score > 60:
            risk_level = "high"
        elif risk_score > 30:
            risk_level = "moderate"
        else:
            risk_level = "low"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "recommendation": self._get_fall_prevention_advice(risk_level),
        }

    def _get_fall_prevention_advice(self, risk_level: str) -> str:
        """跌倒预防建议"""
        if risk_level == "high":
            return "高跌倒风险：建议使用助行器，避免独自行走，加强平衡训练"
        elif risk_level == "moderate":
            return "中等跌倒风险：注意避免不平地面（V11基准：<28.6mm），使用防滑鞋"
        else:
            return "低跌倒风险：保持当前训练，逐步增加行走距离"


if __name__ == "__main__":
    # 测试分类器
    classifier = StrokeGaitClassifier()

    # 模拟患者数据
    patient_data = {
        "stride_length_left": 0.75,  # 患侧显著缩短
        "stride_length_right": 1.10,  # 健侧接近正常
        "cadence": 55,  # 步频偏慢
        "knee_rom_left": 42,  # 患侧膝关节受限
        "knee_rom_right": 62,
        "hip_rom_left": 32,
        "hip_rom_right": 41,
        "stance_time_left": 0.75,
        "stance_time_right": 0.55,
    }

    print("=== 脑卒中步态分类示例 ===\n")

    # 诊断
    diagnosis = classifier.classify_gait_pattern(patient_data)
    print(f"步态模式: {diagnosis['pattern_type']}")
    print(f"严重程度: {diagnosis['severity_score']:.1f}/100")
    print(f"患侧: {diagnosis['affected_side']}")
    print(f"诊断信心: {diagnosis['confidence']*100:.0f}%")

    print(f"\n步态特征:")
    for key, value in diagnosis["features"].items():
        print(f"  {key}: {value}")

    # 康复建议
    print("\n康复建议:")
    recommendations = classifier.generate_recommendations(diagnosis)
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")

    # 跌倒风险评估
    print("\n跌倒风险评估:")
    fall_risk = classifier.assess_fall_risk(patient_data)
    print(f"  风险等级: {fall_risk['risk_level']}")
    print(f"  风险评分: {fall_risk['risk_score']}/100")
    print(f"  风险因素: {', '.join(fall_risk['risk_factors'])}")
    print(f"  预防建议: {fall_risk['recommendation']}")
