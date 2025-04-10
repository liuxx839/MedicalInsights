#verison 3.1 add more details on categorical vars + add condition prob for multi -> categorical analysis + 修改报告输出以优化分类变量统计信息的显示

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import LabelEncoder
import statsmodels.api as sm
import warnings

class DAGRelations:
    def __init__(self, data, dag_edges):
        self.data = data
        self.dag = dag_edges
        self.relations = {}
        self.errors = []
        
    def _handle_categorical(self, s):
        """编码分类变量"""
        return LabelEncoder().fit_transform(s.astype(str))

    def analyze_relations(self):
        """遍历DAG边并分析关系，支持多对一关系"""
        # Suppress specific warnings
        warnings.filterwarnings("ignore", category=stats.DegenerateDataWarning)
        warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")
        
        for relation in self.dag:
            # 支持多对一关系，源可以是单个变量或变量列表
            if isinstance(relation[0], list):
                src_list = relation[0]
                tgt = relation[1]
                # 使用元组而不是列表作为字典键
                edge_key = (tuple(src_list), tgt)
                try:
                    self._analyze_multi_to_one(src_list, tgt, edge_key)
                except Exception as e:
                    error_msg = f"Error analyzing {src_list} -> {tgt}: {str(e)}"
                    print(error_msg)
                    self.errors.append(error_msg)
            else:
                src = relation[0]
                tgt = relation[1]
                edge_key = (src, tgt)
                try:
                    self._analyze_single_to_one(src, tgt, edge_key)
                except Exception as e:
                    error_msg = f"Error analyzing {src} -> {tgt}: {str(e)}"
                    print(error_msg)
                    self.errors.append(error_msg)
        
        return self
    
    def _analyze_single_to_one(self, src, tgt, edge_key):
        """分析单个变量到单个变量的关系"""
        # 检查列是否存在
        if src not in self.data.columns or tgt not in self.data.columns:
            error_msg = f"Error analyzing {src} -> {tgt}: One or both columns don't exist in the dataframe"
            print(error_msg)
            self.errors.append(error_msg)
            return
            
        # 处理缺失值
        if self.data[src].isna().any() or self.data[tgt].isna().any():
            print(f"Warning: {src} or {tgt} contains missing values. Dropping NA rows for this analysis.")
            temp_data = self.data.dropna(subset=[src, tgt])
            if len(temp_data) == 0:
                error_msg = f"Error analyzing {src} -> {tgt}: No valid data after dropping NA values"
                print(error_msg)
                self.errors.append(error_msg)
                return
        else:
            temp_data = self.data
        
        src_type = temp_data[src].dtype
        tgt_type = temp_data[tgt].dtype
        
        print(f"Analyzing {src} -> {tgt}...")
        
        # 数值 -> 数值 (回归分析)
        if np.issubdtype(src_type, np.number) and np.issubdtype(tgt_type, np.number):
            # 使用LinearRegression获取系数和截距
            model = LinearRegression().fit(temp_data[[src]], temp_data[tgt])
            
            # 使用statsmodels获取R2和p值
            x = sm.add_constant(temp_data[src])
            sm_model = sm.OLS(temp_data[tgt], x).fit()
            r2 = sm_model.rsquared
            # 使用.iloc而不是索引访问
            p_values = sm_model.pvalues.iloc[1] if len(sm_model.pvalues) > 1 else None
            
            self.relations[edge_key] = {
                'type': 'numeric->numeric',
                'coef': model.coef_[0],
                'intercept': model.intercept_,
                'r2': r2,
                'p_value': p_values
            }
        
        # 分类 -> 数值 (ANOVA)
        elif not np.issubdtype(src_type, np.number) and np.issubdtype(tgt_type, np.number):
            groups = temp_data.groupby(src)[tgt].apply(list)
            if len(groups) <= 1:
                error_msg = f"Error analyzing {src} -> {tgt}: Need at least two groups for ANOVA"
                print(error_msg)
                self.errors.append(error_msg)
                return
                
            # 移除空组和只有一个元素的组
            valid_groups = []
            for g in groups:
                if len(g) > 1:  # 确保每组至少有两个元素
                    valid_groups.append(g)
            
            if len(valid_groups) <= 1:
                error_msg = f"Error analyzing {src} -> {tgt}: Need at least two groups with multiple data points for ANOVA"
                print(error_msg)
                self.errors.append(error_msg)
                return
                
            try:
                f_val, p_val = stats.f_oneway(*valid_groups)
                
                # 计算每个类别的详细统计信息
                category_stats = temp_data.groupby(src)[tgt].agg(['mean', 'std', 'count', 'min', 'max'])
                # 计算总体均值用于比较
                total_mean = temp_data[tgt].mean()
                
                # 识别显著差异的类别（基于均值与总体均值的差异）
                significant_categories = []
                for cat, row in category_stats.iterrows():
                    if abs(row['mean'] - total_mean) > (temp_data[tgt].std() / 2):  # 使用半个标准差作为阈值
                        direction = "higher" if row['mean'] > total_mean else "lower"
                        significant_categories.append((cat, row['mean'], direction))
                
                self.relations[edge_key] = {
                    'type': 'categorical->numeric',
                    'f_value': f_val,
                    'p_value': p_val,
                    'category_stats': category_stats,
                    'total_mean': total_mean,
                    'total_std': temp_data[tgt].std(),
                    'significant_categories': significant_categories
                }
            except Exception as e:
                error_msg = f"Error with ANOVA for {src} -> {tgt}: {str(e)}"
                print(error_msg)
                self.errors.append(error_msg)
        
        # 分类 -> 分类 (卡方检验)
        elif not np.issubdtype(src_type, np.number) and not np.issubdtype(tgt_type, np.number):
            contingency = pd.crosstab(temp_data[src], temp_data[tgt])
            
            # 检查列联表是否有效
            if contingency.shape[0] <= 1 or contingency.shape[1] <= 1:
                error_msg = f"Error analyzing {src} -> {tgt}: Contingency table needs at least 2x2 dimensions"
                print(error_msg)
                self.errors.append(error_msg)
                return
                
            chi2, p, dof, expected = stats.chi2_contingency(contingency)
            
            # 安全计算Cramer's V
            denominator = temp_data.shape[0] * (min(contingency.shape) - 1)
            cramers_v = np.sqrt(chi2 / denominator) if denominator > 0 else None
            
            if cramers_v is None:
                print(f"Warning: Could not calculate Cramer's V for {src} -> {tgt} (division by zero)")
            
            # 计算每个组合的条件概率
            row_totals = contingency.sum(axis=1)
            col_totals = contingency.sum(axis=0)
            total = contingency.sum().sum()
            
            # 计算每个组合的观察值与期望值的差异
            diff = contingency.values - expected
            contrib = (diff ** 2) / expected
            
            # 找出贡献最大的单元格（表示最显著的关联）
            max_contrib_idx = np.unravel_index(np.argmax(contrib), contrib.shape)
            max_contrib_src = contingency.index[max_contrib_idx[0]]
            max_contrib_tgt = contingency.columns[max_contrib_idx[1]]
            
            # 计算条件概率
            cond_probs = {}
            for i, src_val in enumerate(contingency.index):
                for j, tgt_val in enumerate(contingency.columns):
                    if row_totals[src_val] > 0:
                        prob = contingency.iloc[i, j] / row_totals[src_val]
                        cond_probs[(src_val, tgt_val)] = prob
            
            # 找出条件概率最高的组合
            if cond_probs:
                max_prob_combo = max(cond_probs.items(), key=lambda x: x[1])
            else:
                max_prob_combo = None
            
            self.relations[edge_key] = {
                'type': 'categorical->categorical',
                'chi2': chi2,
                'p_value': p,
                'cramers_v': cramers_v,
                'contingency_table': contingency,
                'expected_counts': pd.DataFrame(expected, index=contingency.index, columns=contingency.columns),
                'strongest_association': (max_contrib_src, max_contrib_tgt),
                'strongest_association_value': contingency.loc[max_contrib_src, max_contrib_tgt],
                'strongest_association_expected': expected[max_contrib_idx],
                'max_conditional_probability': max_prob_combo
            }
        
        # 数值 -> 分类 (逻辑回归)
        else:
            # 确保我们有足够的不同类别
            unique_categories = temp_data[tgt].nunique()
            if unique_categories <= 1:
                error_msg = f"Error analyzing {src} -> {tgt}: Target variable has only {unique_categories} category"
                print(error_msg)
                self.errors.append(error_msg)
                return
                
            encoded_tgt = self._handle_categorical(temp_data[tgt])
            model = LinearRegression().fit(temp_data[[src]], encoded_tgt)
            self.relations[edge_key] = {
                'type': 'numeric->categorical',
                'coef': model.coef_[0],
                'intercept': model.intercept_
            }
    
    def _analyze_multi_to_one(self, src_list, tgt, edge_key):
        """分析多个变量到单个变量的关系"""
        # 检查列是否存在
        missing_cols = [col for col in src_list + [tgt] if col not in self.data.columns]
        if missing_cols:
            error_msg = f"Error analyzing {src_list} -> {tgt}: Missing columns: {missing_cols}"
            print(error_msg)
            self.errors.append(error_msg)
            return
            
        # 处理缺失值
        cols_to_check = src_list + [tgt]
        if self.data[cols_to_check].isna().any().any():
            print(f"Warning: {src_list} or {tgt} contains missing values. Dropping NA rows for this analysis.")
            temp_data = self.data.dropna(subset=cols_to_check)
            if len(temp_data) == 0:
                error_msg = f"Error analyzing {src_list} -> {tgt}: No valid data after dropping NA values"
                print(error_msg)
                self.errors.append(error_msg)
                return
        else:
            temp_data = self.data
        
        # 检查源变量和目标变量类型
        tgt_type = temp_data[tgt].dtype
        src_types = [temp_data[src].dtype for src in src_list]
        
        print(f"Analyzing {src_list} -> {tgt}...")
        
        # 所有源变量均为数值 -> 数值 (多元回归)
        if np.issubdtype(tgt_type, np.number) and all(np.issubdtype(t, np.number) for t in src_types):
            # 使用LinearRegression获取系数和截距
            model = LinearRegression().fit(temp_data[src_list], temp_data[tgt])
            
            # 使用statsmodels获取R2和p值
            x = sm.add_constant(temp_data[src_list])
            sm_model = sm.OLS(temp_data[tgt], x).fit()
            r2 = sm_model.rsquared
            
            # 使用正确的方法获取p值
            p_values = []
            for i, var in enumerate(src_list):
                if var in sm_model.pvalues.index:
                    p_values.append(sm_model.pvalues[var])
                else:
                    # 如果变量名不在索引中，尝试按位置获取（跳过常量项）
                    if i + 1 < len(sm_model.pvalues):
                        p_values.append(sm_model.pvalues.iloc[i + 1])
                    else:
                        p_values.append(None)
            
            self.relations[edge_key] = {
                'type': 'multi-numeric->numeric',
                'coefs': {src: coef for src, coef in zip(src_list, model.coef_)},
                'intercept': model.intercept_,
                'r2': r2,
                'p_values': {src: p for src, p in zip(src_list, p_values)}
            }
        
        # 混合类型 -> 数值 (ANCOVA)
        elif np.issubdtype(tgt_type, np.number):
            # 将分类变量和数值变量分离
            cat_vars = [src for src, t in zip(src_list, src_types) if not np.issubdtype(t, np.number)]
            num_vars = [src for src, t in zip(src_list, src_types) if np.issubdtype(t, np.number)]
            
            if not cat_vars or not num_vars:
                # 如果没有混合类型，则按照单一类型处理
                if not cat_vars:  # 全部是数值变量
                    # 已经在前一个条件处理了
                    return
                else:  # 全部是分类变量
                    # 创建设计矩阵
                    formula = f"{tgt} ~ " + " + ".join(cat_vars)
                    model = sm.formula.ols(formula, data=temp_data).fit()
                    
                    # 获取p值
                    p_values = {}
                    for var in cat_vars:
                        if var in model.pvalues.index:
                            p_values[var] = model.pvalues[var]
                        else:
                            p_values[var] = None
                    
                    # 为每个分类变量添加类别均值信息
                    category_stats = {}
                    for var in cat_vars:
                        category_stats[var] = temp_data.groupby(var)[tgt].agg(['mean', 'std', 'count'])
                    
                    self.relations[edge_key] = {
                        'type': 'multi-categorical->numeric',
                        'r2': model.rsquared,
                        'p_values': p_values,
                        'f_value': model.fvalue,
                        'overall_p_value': model.f_pvalue,
                        'category_stats': category_stats
                    }
                    return
            
            # 创建混合模型
            formula = f"{tgt} ~ " + " + ".join(src_list)
            try:
                model = sm.formula.ols(formula, data=temp_data).fit()
                
                # 获取p值
                p_values = {}
                for var in src_list:
                    if var in model.pvalues.index:
                        p_values[var] = model.pvalues[var]
                    else:
                        p_values[var] = None
                
                # 为分类变量添加类别均值信息
                category_stats = {}
                for var in cat_vars:
                    category_stats[var] = temp_data.groupby(var)[tgt].agg(['mean', 'std', 'count'])
                
                self.relations[edge_key] = {
                    'type': 'mixed->numeric',
                    'r2': model.rsquared,
                    'p_values': p_values,
                    'f_value': model.fvalue,
                    'overall_p_value': model.f_pvalue,
                    'category_stats': category_stats
                }
            except Exception as e:
                error_msg = f"Error with ANCOVA for {src_list} -> {tgt}: {str(e)}"
                print(error_msg)
                self.errors.append(error_msg)
        
        # # 混合类型或全部是分类变量 -> 分类 (暂不支持详细分析)
        # else:
        #     error_msg = f"Complex relationship {src_list} -> {tgt} (with target being categorical) is not fully supported yet"
        #     print(error_msg)
        #     self.errors.append(error_msg)
        # 混合类型或全部是分类变量 -> 分类 (使用条件概率分析)
        else:
            # 对目标变量进行编码
            encoded_tgt = self._handle_categorical(temp_data[tgt])
            target_categories = temp_data[tgt].unique()
            
            # 分离分类变量和数值变量
            cat_vars = [src for src, t in zip(src_list, src_types) if not np.issubdtype(t, np.number)]
            num_vars = [src for src, t in zip(src_list, src_types) if np.issubdtype(t, np.number)]
            
            # 计算条件概率
            conditional_probs = {}
            
            # 对于每个分类变量，计算条件概率
            for cat_var in cat_vars:
                var_categories = temp_data[cat_var].unique()
                prob_table = pd.DataFrame(index=var_categories, columns=target_categories)
                
                for cat in var_categories:
                    subset = temp_data[temp_data[cat_var] == cat]
                    if len(subset) > 0:
                        for tgt_cat in target_categories:
                            prob = (subset[tgt] == tgt_cat).mean()
                            prob_table.loc[cat, tgt_cat] = prob
                
                conditional_probs[cat_var] = prob_table
            
            # 对于数值变量，计算相关性和影响
            num_var_effects = {}
            for num_var in num_vars:
                # 对于每个目标类别，计算数值变量的均值和标准差
                stats = {}
                for tgt_cat in target_categories:
                    subset = temp_data[temp_data[tgt] == tgt_cat]
                    if len(subset) > 0:
                        stats[tgt_cat] = {
                            'mean': subset[num_var].mean(),
                            'std': subset[num_var].std(),
                            'count': len(subset)
                        }
                
                # 计算ANOVA以检验不同目标类别之间的数值变量差异
                groups = [temp_data[temp_data[tgt] == cat][num_var].dropna() for cat in target_categories]
                valid_groups = [g for g in groups if len(g) > 1]
                
                if len(valid_groups) > 1:
                    try:
                        f_val, p_val = stats.f_oneway(*valid_groups)
                        num_var_effects[num_var] = {
                            'stats': stats,
                            'f_value': f_val,
                            'p_value': p_val
                        }
                    except Exception as e:
                        print(f"Error during ANOVA for {num_var}: {str(e)}")
                        num_var_effects[num_var] = {
                            'stats': stats,
                            'error': str(e)
                        }
                else:
                    num_var_effects[num_var] = {
                        'stats': stats,
                        'error': "Not enough valid groups for ANOVA"
                    }
            
            # 计算组合变量的条件概率 (对于前两个分类变量)
            combined_probs = None
            if len(cat_vars) >= 2:
                first_var = cat_vars[0]
                second_var = cat_vars[1]
                
                # 创建组合变量
                temp_data['combined'] = temp_data[first_var].astype(str) + "_" + temp_data[second_var].astype(str)
                combined_categories = temp_data['combined'].unique()
                
                # 计算组合条件概率
                prob_table = pd.DataFrame(index=combined_categories, columns=target_categories)
                
                for comb in combined_categories:
                    subset = temp_data[temp_data['combined'] == comb]
                    if len(subset) > 0:
                        for tgt_cat in target_categories:
                            prob = (subset[tgt] == tgt_cat).mean()
                            prob_table.loc[comb, tgt_cat] = prob
                
                # 找出最显著的组合
                max_probs = {}
                for tgt_cat in target_categories:
                    max_prob = prob_table[tgt_cat].max()
                    max_comb = prob_table[tgt_cat].idxmax()
                    max_probs[tgt_cat] = (max_comb, max_prob)
                
                combined_probs = {
                    'vars': [first_var, second_var],
                    'prob_table': prob_table,
                    'max_probs': max_probs
                }
            
            # Replace the model fitting section in the mixed->categorical analysis with this:

            # 计算整体预测能力 (使用全部变量的简单模型)
            try:
                # 对分类变量进行独热编码
                dummy_data = pd.get_dummies(temp_data[cat_vars], drop_first=True) if cat_vars else pd.DataFrame(index=temp_data.index)
                
                # 添加数值变量
                if num_vars:
                    # 确保所有数值变量都是浮点型
                    num_data = temp_data[num_vars].astype(float)
                    dummy_data = pd.concat([dummy_data, num_data], axis=1)
                
                # 拟合简单模型
                if len(dummy_data.columns) > 0:
                    # 添加常数项
                    dummy_data_with_const = sm.add_constant(dummy_data)
                    
                    # 确保数据可用于模型拟合
                    dummy_data_with_const = dummy_data_with_const.astype(float)
                    encoded_tgt_series = pd.Series(encoded_tgt).astype(float)
                    
                    # 检查是否有缺失值或无限值
                    if dummy_data_with_const.isnull().any().any() or np.isinf(dummy_data_with_const.values).any():
                        dummy_data_with_const = dummy_data_with_const.fillna(0)
                        dummy_data_with_const = dummy_data_with_const.replace([np.inf, -np.inf], 0)
                    
                    try:
                        model = sm.Logit(encoded_tgt_series, dummy_data_with_const).fit(disp=0)
                        prediction_quality = {
                            'model_type': 'logit',
                            'accuracy': model.pred_table()[0, 0] + model.pred_table()[1, 1] / model.pred_table().sum(),
                            'pseudo_r2': model.prsquared
                        }
                    except Exception as e:
                        # 如果Logit模型失败，尝试使用LinearRegression
                        model = LinearRegression().fit(dummy_data.values, encoded_tgt)
                        # 计算预测准确度
                        preds = model.predict(dummy_data.values)
                        preds_binary = (preds > 0.5).astype(int)
                        accuracy = (preds_binary == encoded_tgt).mean()
                        prediction_quality = {
                            'model_type': 'linear',
                            'accuracy': accuracy,
                            'r2': model.score(dummy_data.values, encoded_tgt)
                        }
                else:
                    prediction_quality = {
                        'error': "No variables available for modeling"
                    }
            except Exception as e:
                prediction_quality = {
                    'error': f"Error during model fitting: {str(e)}"
                }
            
            # 储存结果
            self.relations[edge_key] = {
                'type': 'mixed->categorical' if num_vars else 'multi-categorical->categorical',
                'conditional_probs': conditional_probs,
                'num_var_effects': num_var_effects if num_vars else None,
                'combined_probs': combined_probs,
                'prediction_quality': prediction_quality,
                'target_distribution': {cat: (temp_data[tgt] == cat).mean() for cat in target_categories}
            }

    def print_report(self, output_to_console=True):
        """输出关系报告并返回文本格式的报告"""
        report_lines = []
        
        if not self.relations:
            message = "No valid relationships found!"
            if output_to_console:
                print(message)
            report_lines.append(message)
            return '\n'.join(report_lines)
        
        for edge, metrics in self.relations.items():
            # 处理单变量关系
            if not isinstance(edge[0], tuple):
                header = f"\nRelationship {edge[0]} -> {edge[1]}"
                type_info = f"Type: {metrics['type']}"
                
                if output_to_console:
                    print(header)
                    print(type_info)
                
                report_lines.append(header)
                report_lines.append(type_info)
                
                # 处理categorical->numeric关系
                if metrics['type'] == 'categorical->numeric':
                    # 打印基本统计指标
                    for k in ['f_value', 'p_value']:
                        if metrics.get(k) is not None:
                            line = f"{k:>15}: {metrics[k]:.4f}"
                            if output_to_console:
                                print(line)
                            report_lines.append(line)
                    
                    # 添加解释
                    significance = "significant" if metrics.get('p_value', 1) < 0.05 else "not significant"
                    interpretation = f"\nThe relationship is statistically {significance} (p={metrics.get('p_value', 'N/A'):.4f})."
                    if output_to_console:
                        print(interpretation)
                    report_lines.append(interpretation)
                    
                    # 打印每个类别的统计信息
                    cat_stats_header = "\nCategory Statistics:"
                    if output_to_console:
                        print(cat_stats_header)
                    report_lines.append(cat_stats_header)
                    
                    if 'category_stats' in metrics:
                        # 格式化表格头部
                        header_line = f"{'Category':>15} | {'Count':>8} | {'Mean':>10} | {'Std Dev':>10} | {'% Diff from Mean':>15}"
                        divider = "-" * len(header_line)
                        
                        if output_to_console:
                            print(header_line)
                            print(divider)
                        report_lines.append(header_line)
                        report_lines.append(divider)
                        
                        # 检查类别数量，如果超过15个，只显示最显著的类别
                        category_stats = metrics['category_stats']
                        if len(category_stats) > 15:
                            # 计算每个类别的显著性分数（基于样本量和与均值的差异）
                            significance_scores = []
                            for cat_name, row in category_stats.iterrows():
                                # 计算与总体均值的百分比差异
                                pct_diff = abs((row['mean'] - metrics['total_mean']) / metrics['total_mean'] * 100) if metrics['total_mean'] != 0 else float('inf')
                                # 显著性分数 = 样本量 * 百分比差异
                                significance_score = row['count'] * pct_diff
                                significance_scores.append((cat_name, row, significance_score))
                            
                            # 按显著性分数排序并选择前15个
                            significance_scores.sort(key=lambda x: x[2], reverse=True)
                            top_categories = significance_scores[:15]
                            
                            # 添加说明
                            note_line = f"Note: Showing only the 15 most significant categories out of {len(category_stats)} total categories."
                            if output_to_console:
                                print(note_line)
                            report_lines.append(note_line)
                            
                            # 打印选定的类别
                            for cat_name, row, _ in top_categories:
                                # 计算与总体均值的百分比差异
                                pct_diff = ((row['mean'] - metrics['total_mean']) / metrics['total_mean'] * 100) if metrics['total_mean'] != 0 else float('inf')
                                
                                # 格式化输出
                                line = f"{str(cat_name):>15} | {int(row['count']):>8} | {row['mean']:>10.4f} | {row['std']:>10.4f} | {pct_diff:>15.2f}%"
                                if output_to_console:
                                    print(line)
                                report_lines.append(line)
                        else:
                            # 打印所有类别
                            for cat_name, row in category_stats.iterrows():
                                # 计算与总体均值的百分比差异
                                pct_diff = ((row['mean'] - metrics['total_mean']) / metrics['total_mean'] * 100) if metrics['total_mean'] != 0 else float('inf')
                                
                                # 格式化输出
                                line = f"{str(cat_name):>15} | {int(row['count']):>8} | {row['mean']:>10.4f} | {row['std']:>10.4f} | {pct_diff:>15.2f}%"
                                if output_to_console:
                                    print(line)
                                report_lines.append(line)
                    
                    # 添加显著差异类别的解释
                    if metrics.get('significant_categories'):
                        sig_header = "\nCategories with Significant Differences:"
                        if output_to_console:
                            print(sig_header)
                        report_lines.append(sig_header)
                        
                        # 如果显著类别超过10个，只显示最显著的10个
                        sig_categories = metrics['significant_categories']
                        if len(sig_categories) > 10:
                            # 按照与均值的差异程度排序
                            sig_categories.sort(key=lambda x: abs(x[1] - metrics['total_mean']), reverse=True)
                            sig_categories = sig_categories[:10]
                            
                            # 添加说明
                            note_line = f"Note: Showing only the 10 most significant categories out of {len(metrics['significant_categories'])} significant categories."
                            if output_to_console:
                                print(note_line)
                            report_lines.append(note_line)
                        
                        for cat, mean, direction in sig_categories:
                            line = f"- {cat}: {mean:.4f} ({direction} than overall mean of {metrics['total_mean']:.4f})"
                            if output_to_console:
                                print(line)
                            report_lines.append(line)
                
                # 处理categorical->categorical关系
                elif metrics['type'] == 'categorical->categorical':
                    # 打印基本统计指标
                    for k in ['chi2', 'p_value', 'cramers_v']:
                        if metrics.get(k) is not None:
                            line = f"{k:>15}: {metrics[k]:.4f}"
                            if output_to_console:
                                print(line)
                            report_lines.append(line)
                    
                    # 添加解释
                    significance = "significant" if metrics.get('p_value', 1) < 0.05 else "not significant"
                    association = "strong" if metrics.get('cramers_v', 0) > 0.3 else ("moderate" if metrics.get('cramers_v', 0) > 0.1 else "weak")
                    interpretation = f"\nThe association is statistically {significance} (p={metrics.get('p_value', 'N/A'):.4f}) and {association} (Cramer's V={metrics.get('cramers_v', 'N/A'):.4f})."
                    if output_to_console:
                        print(interpretation)
                    report_lines.append(interpretation)
                    
                    # 打印最强关联
                    if 'strongest_association' in metrics:
                        src_val, tgt_val = metrics['strongest_association']
                        strongest_line = f"\nStrongest association: When {edge[0]} is '{src_val}', {edge[1]} is most likely to be '{tgt_val}'"
                        strongest_detail = f"  Observed: {metrics['strongest_association_value']}, Expected: {metrics['strongest_association_expected']:.2f}"
                        
                        if output_to_console:
                            print(strongest_line)
                            print(strongest_detail)
                        report_lines.append(strongest_line)
                        report_lines.append(strongest_detail)
                    
                    # 打印最高条件概率
                    if metrics.get('max_conditional_probability'):
                        (src_val, tgt_val), prob = metrics['max_conditional_probability']
                        prob_line = f"\nHighest conditional probability: P({edge[1]}='{tgt_val}' | {edge[0]}='{src_val}') = {prob:.4f}"
                        if output_to_console:
                            print(prob_line)
                        report_lines.append(prob_line)
                
                ###
                # Add this to the print_report method where it handles different relationship types
                # Inside the "else" block where it handles multi-variable relationships

                elif metrics['type'] in ['mixed->categorical', 'multi-categorical->categorical']:
                    # Print target distribution
                    dist_header = "\nTarget Variable Distribution:"
                    if output_to_console:
                        print(dist_header)
                    report_lines.append(dist_header)
                    
                    for cat, prob in metrics['target_distribution'].items():
                        line = f"{str(cat):>15}: {prob:.4f} ({prob*100:.1f}%)"
                        if output_to_console:
                            print(line)
                        report_lines.append(line)
                    
                    # Print conditional probabilities for categorical variables
                    if 'conditional_probs' in metrics:
                        cond_header = "\nConditional Probabilities:"
                        if output_to_console:
                            print(cond_header)
                        report_lines.append(cond_header)
                        
                        for var, prob_table in metrics['conditional_probs'].items():
                            var_header = f"\nVariable: {var}"
                            if output_to_console:
                                print(var_header)
                            report_lines.append(var_header)
                            
                            # Format table header with target categories
                            header_parts = ["Category"] + [f"{col}" for col in prob_table.columns]
                            header_line = " | ".join(f"{part:>15}" for part in header_parts)
                            divider = "-" * len(header_line)
                            
                            if output_to_console:
                                print(header_line)
                                print(divider)
                            report_lines.append(header_line)
                            report_lines.append(divider)
                            
                            # Print each row
                            for idx, row in prob_table.iterrows():
                                row_parts = [str(idx)] + [f"{val:.4f}" if not pd.isna(val) else "N/A" for val in row]
                                line = " | ".join(f"{part:>15}" for part in row_parts)
                                if output_to_console:
                                    print(line)
                                report_lines.append(line)
                            
                            # Find and highlight most predictive categories
                            most_predictive = []
                            for col in prob_table.columns:
                                if not prob_table[col].isna().all():
                                    max_val = prob_table[col].max()
                                    max_idx = prob_table[col].idxmax()
                                    # Only include if probability is significantly higher than base rate
                                    if max_val > metrics['target_distribution'].get(col, 0) * 1.5:
                                        most_predictive.append((max_idx, col, max_val))
                            
                            if most_predictive:
                                predict_header = "\nMost predictive categories:"
                                if output_to_console:
                                    print(predict_header)
                                report_lines.append(predict_header)
                                
                                for cat, tgt_cat, prob in most_predictive:
                                    base_rate = metrics['target_distribution'].get(tgt_cat, 0)
                                    lift = prob / base_rate if base_rate > 0 else float('inf')
                                    line = f"- When {var} is '{cat}', {tgt} is '{tgt_cat}' with probability {prob:.4f} ({lift:.2f}x base rate)"
                                    if output_to_console:
                                        print(line)
                                    report_lines.append(line)
                    
                    # Print combined variable effects
                    if metrics.get('combined_probs'):
                        combined_header = f"\nCombined Effect of {' and '.join(metrics['combined_probs']['vars'])}:"
                        if output_to_console:
                            print(combined_header)
                        report_lines.append(combined_header)
                        
                        # Print most significant combinations
                        sig_header = "\nMost significant combinations:"
                        if output_to_console:
                            print(sig_header)
                        report_lines.append(sig_header)
                        
                        for tgt_cat, (comb, prob) in metrics['combined_probs']['max_probs'].items():
                            base_rate = metrics['target_distribution'].get(tgt_cat, 0)
                            lift = prob / base_rate if base_rate > 0 else float('inf')
                            line = f"- For {tgt}='{tgt_cat}': Combination '{comb}' with probability {prob:.4f} ({lift:.2f}x base rate)"
                            if output_to_console:
                                print(line)
                            report_lines.append(line)
                    
                    # Print numerical variable effects
                    if metrics.get('num_var_effects'):
                        num_header = "\nNumerical Variable Effects:"
                        if output_to_console:
                            print(num_header)
                        report_lines.append(num_header)
                        
                        for var, effects in metrics['num_var_effects'].items():
                            var_header = f"\nVariable: {var}"
                            if output_to_console:
                                print(var_header)
                            report_lines.append(var_header)
                            
                            if 'error' in effects:
                                error_line = f"Error: {effects['error']}"
                                if output_to_console:
                                    print(error_line)
                                report_lines.append(error_line)
                                continue
                            
                            # Print F-test results
                            if 'f_value' in effects and 'p_value' in effects:
                                f_line = f"F-value: {effects['f_value']:.4f}, p-value: {effects['p_value']:.4f}"
                                significance = "significant" if effects['p_value'] < 0.05 else "not significant"
                                sig_line = f"The effect is statistically {significance}"
                                
                                if output_to_console:
                                    print(f_line)
                                    print(sig_line)
                                report_lines.append(f_line)
                                report_lines.append(sig_line)
                            
                            # Print statistics for each target category
                            stats_header = "\nStatistics by target category:"
                            if output_to_console:
                                print(stats_header)
                            report_lines.append(stats_header)
                            
                            # Format table header
                            header_line = f"{'Target Category':>20} | {'Count':>8} | {'Mean':>10} | {'Std Dev':>10}"
                            divider = "-" * len(header_line)
                            
                            if output_to_console:
                                print(header_line)
                                print(divider)
                            report_lines.append(header_line)
                            report_lines.append(divider)
                            
                            # Print statistics for each category
                            for cat, stats in effects['stats'].items():
                                line = f"{str(cat):>20} | {int(stats['count']):>8} | {stats['mean']:>10.4f} | {stats['std']:>10.4f}"
                                if output_to_console:
                                    print(line)
                                report_lines.append(line)
                    
                    # Print overall prediction quality
                    if 'prediction_quality' in metrics:
                        pred_header = "\nOverall Prediction Quality:"
                        if output_to_console:
                            print(pred_header)
                        report_lines.append(pred_header)
                        
                        pred_quality = metrics['prediction_quality']
                        if 'error' in pred_quality:
                            error_line = f"Error: {pred_quality['error']}"
                            if output_to_console:
                                print(error_line)
                            report_lines.append(error_line)
                        else:
                            for k, v in pred_quality.items():
                                if k != 'model_type':
                                    line = f"{k:>15}: {v:.4f}" if isinstance(v, float) else f"{k:>15}: {v}"
                                    if output_to_console:
                                        print(line)
                                    report_lines.append(line)
                            
                            # Add interpretation
                            accuracy = pred_quality.get('accuracy', 0)
                            if accuracy > 0.8:
                                quality = "excellent"
                            elif accuracy > 0.7:
                                quality = "good"
                            elif accuracy > 0.6:
                                quality = "moderate"
                            else:
                                quality = "poor"
                                
                            interp_line = f"\nThe combined predictive power of all variables is {quality} (accuracy: {accuracy:.4f})"
                            if output_to_console:
                                print(interp_line)
                            report_lines.append(interp_line)
                # 处理其他类型关系
                else:
                    for k, v in metrics.items():
                        if k != 'type':
                            if v is None:
                                line = f"{k:>15}: Not calculable"
                            else:
                                line = f"{k:>15}: {v:.4f}" if isinstance(v, float) else f"{k:>15}: {v}"
                            
                            if output_to_console:
                                print(line)
                            report_lines.append(line)
            
            # 处理多变量关系
            else:
                src_tuple, tgt = edge
                src_list = list(src_tuple)  # 转换回列表以便打印
                header = f"\nRelationship {src_list} -> {tgt}"
                type_info = f"Type: {metrics['type']}"
                
                if output_to_console:
                    print(header)
                    print(type_info)
                
                report_lines.append(header)
                report_lines.append(type_info)
                
                if metrics['type'] == 'multi-numeric->numeric':
                    r2_line = f"{'R-squared':>15}: {metrics['r2']:.4f}"
                    intercept_line = f"{'Intercept':>15}: {metrics['intercept']:.4f}"
                    coef_header = "\nCoefficients and p-values:"
                    
                    if output_to_console:
                        print(r2_line)
                        print(intercept_line)
                        print(coef_header)
                    
                    report_lines.append(r2_line)
                    report_lines.append(intercept_line)
                    report_lines.append(coef_header)
                    
                    for src in src_list:
                        coef_val = metrics['coefs'].get(src, None)
                        p_val = metrics['p_values'].get(src, None)
                        coef_str = f"{coef_val:.4f}" if coef_val is not None else "Not calculable"
                        p_str = f"(p={p_val:.4f})" if p_val is not None else "(p=Not calculable)"
                        line = f"{src:>15}: {coef_str} {p_str}"
                        
                        if output_to_console:
                            print(line)
                        report_lines.append(line)
                
                elif metrics['type'] in ['multi-categorical->numeric', 'mixed->numeric']:
                    r2_line = f"{'R-squared':>15}: {metrics['r2']:.4f}"
                    f_line = f"{'F-value':>15}: {metrics['f_value']:.4f}"
                    p_line = f"{'Overall p-value':>15}: {metrics['overall_p_value']:.4f}"
                    p_header = "\nIndividual p-values:"
                    
                    if output_to_console:
                        print(r2_line)
                        print(f_line)
                        print(p_line)
                        print(p_header)
                    
                    report_lines.append(r2_line)
                    report_lines.append(f_line)
                    report_lines.append(p_line)
                    report_lines.append(p_header)
                    
                    for var, p in metrics['p_values'].items():
                        if p is not None:
                            line = f"{var:>15}: {p:.4f}"
                        else:
                            line = f"{var:>15}: Not calculable"
                        
                        if output_to_console:
                            print(line)
                        report_lines.append(line)
                    
                    # 添加分类变量的类别统计信息
                    if 'category_stats' in metrics:
                        cat_stats_header = "\nCategory Statistics:"
                        if output_to_console:
                            print(cat_stats_header)
                        report_lines.append(cat_stats_header)
                        
                        for var, stats_df in metrics['category_stats'].items():
                            var_header = f"\nVariable: {var}"
                            if output_to_console:
                                print(var_header)
                            report_lines.append(var_header)
                            
                            # 格式化表格头部
                            header_line = f"{'Category':>15} | {'Count':>8} | {'Mean':>10} | {'Std Dev':>10}"
                            divider = "-" * len(header_line)
                            
                            if output_to_console:
                                print(header_line)
                                print(divider)
                            report_lines.append(header_line)
                            report_lines.append(divider)
                            
                            # 打印每个类别的详细信息
                            for cat_name, row in stats_df.iterrows():
                                line = f"{str(cat_name):>15} | {int(row['count']):>8} | {row['mean']:>10.4f} | {row['std']:>10.4f}"
                                if output_to_console:
                                    print(line)
                                report_lines.append(line)
                
                else:
                    for k, v in metrics.items():
                        if k != 'type':
                            if v is None:
                                line = f"{k:>15}: Not calculable"
                            else:
                                line = f"{k:>15}: {v:.4f}" if isinstance(v, float) else f"{k:>15}: {v}"
                            
                            if output_to_console:
                                print(line)
                            report_lines.append(line)
        
        if self.errors:
            error_header = "\n\nErrors encountered during analysis:"
            
            if output_to_console:
                print(error_header)
            report_lines.append(error_header)
            
            for i, error in enumerate(self.errors, 1):
                line = f"{i}. {error}"
                
                if output_to_console:
                    print(line)
                report_lines.append(line)
        
        # Return the report as a string
        return '\n'.join(report_lines)
    

# # 示例使用
# if __name__ == "__main__":
#     try:
#         df = pd.read_excel('CV_B1-guangdong1_poc.group_bound.nogongguan_actual.xlsx')
#         print(f"Successfully loaded data with {df.shape[0]} rows and {df.shape[1]} columns")
#     except Exception as e:
#         print(f"Error loading data: {str(e)}")
#         exit(1)

#     # 定义DAG边（支持多对一关系）
#     dag_edges = [
#         ('pt_group', 'group'),
#         ('group', 'hco_cd'),
#         ('group', 'group_type'),
#         ('city_old', 'county'),
#         ('county', 'hco_cd'),
#         ('hco_cd', 'hco_nm'),
#         ('hco_cd', 'latitude'),
#         ('hco_cd', 'longitude'),
#         ('city_old', 'city'),
#         ('productivity_ly', 'productivity'),
#         ('fte', 'productivity'),
#         ('potential', 'productivity'),
#         # 多对一关系示例
#         (['productivity_ly', 'fte'], 'productivity'),
#         (['productivity_ly', 'fte', 'potential'], 'productivity')
#     ]

#     analyzer = DAGRelations(df, dag_edges)
#     analyzer.analyze_relations().print_report()