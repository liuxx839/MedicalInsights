import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# 设置绘图风格
sns.set_theme(style="whitegrid")

def create_visualizations(dag_analyzer, data_desc_analyzer, df):
    """
    根据分析结果生成一系列可视化图表。

    参数:
    dag_analyzer (DAGRelations): 已完成分析的DAGRelations对象。
    data_desc_analyzer (DataDescription): 已完成分析的DataDescription对象。
    df (pd.DataFrame): 原始数据。

    返回:
    dict: 一个字典，键是图表标题，值是matplotlib的Figure对象。
    """
    visualizations = {}

    # --- 1. 单变量分布图 (来自 DataDescription) ---
    for col, desc in data_desc_analyzer.descriptions.items():
        try:
            if desc['type'] == 'continuous' and desc['count'] > 0:
                fig, ax = plt.subplots(figsize=(8, 5))
                sns.histplot(df[col].dropna(), kde=True, ax=ax)
                ax.set_title(f"Distribution of '{col}'")
                title = f"Distribution: {col}"
                visualizations[title] = fig
                plt.close(fig)

            elif desc['type'] == 'categorical' and desc['count'] > 0:
                # 只展示类别数少于30的变量
                if desc['unique_values'] < 30:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    # 获取前15个类别进行展示
                    top_categories = df[col].value_counts().nlargest(15)
                    sns.barplot(x=top_categories.index, y=top_categories.values, ax=ax, palette="viridis")
                    ax.set_title(f"Top 15 Categories of '{col}'")
                    ax.set_ylabel("Count")
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    title = f"Category Counts: {col}"
                    visualizations[title] = fig
                    plt.close(fig)

        except Exception as e:
            print(f"Could not create visualization for single variable {col}: {e}")

    # --- 2. 变量关系图 (来自 DAGRelations) ---
    for edge, metrics in dag_analyzer.relations.items():
        try:
            # 解析源和目标变量
            src, tgt = edge[0], edge[1]
            title = f"Relationship: {src} -> {tgt}"

            # 单变量 -> 单变量
            if not isinstance(src, tuple):
                if metrics['type'] == 'numeric->numeric':
                    fig, ax = plt.subplots(figsize=(8, 6))
                    sns.regplot(x=src, y=tgt, data=df, ax=ax, line_kws={"color": "red"})
                    ax.set_title(f"{src} vs {tgt} (R²={metrics.get('r2', 0):.2f})")
                    visualizations[title] = fig
                    plt.close(fig)

                elif metrics['type'] == 'categorical->numeric':
                    # 只展示类别数少于30的变量
                    if df[src].nunique() < 30:
                        fig, ax = plt.subplots(figsize=(12, 7))
                        sns.boxplot(x=src, y=tgt, data=df, ax=ax, palette="coolwarm")
                        ax.set_title(f"Distribution of '{tgt}' by '{src}'")
                        plt.xticks(rotation=45, ha='right')
                        plt.tight_layout()
                        visualizations[title] = fig
                        plt.close(fig)

                elif metrics['type'] == 'categorical->categorical':
                    contingency_table = metrics.get('contingency_table')
                    if contingency_table is not None:
                        fig, ax = plt.subplots(figsize=(10, 8))
                        sns.heatmap(contingency_table, annot=True, fmt='d', cmap='YlGnBu', ax=ax)
                        ax.set_title(f"Contingency Heatmap: {src} vs {tgt}")
                        visualizations[title] = fig
                        plt.close(fig)
            
            # 多变量 -> 单变量
            else:
                src_list = list(src)
                # (混合类型或分类) -> 分类
                if metrics['type'] in ['mixed->categorical', 'multi-categorical->categorical']:
                    if 'conditional_probs' in metrics:
                        for var, prob_table in metrics['conditional_probs'].items():
                            # 只绘制类别数较少的
                            if prob_table.shape[0] < 20 and prob_table.shape[1] < 20:
                                fig, ax = plt.subplots(figsize=(12, 8))
                                sns.heatmap(prob_table.astype(float), annot=True, fmt='.2f', cmap='coolwarm', ax=ax)
                                ax.set_title(f"Conditional Probability: P({tgt} | {var})")
                                viz_title = f"Conditional Probability Heatmap: {var} -> {tgt}"
                                visualizations[viz_title] = fig
                                plt.close(fig)
                
                # (混合类型或数值) -> 数值
                elif metrics['type'] in ['mixed->numeric', 'multi-numeric->numeric']:
                    # 识别数值和分类源变量
                    num_vars = [s for s in src_list if pd.api.types.is_numeric_dtype(df[s])]
                    cat_vars = [s for s in src_list if not pd.api.types.is_numeric_dtype(df[s])]

                    # 如果有一个数值和一个分类变量，绘制带色调的散点图
                    if len(num_vars) == 1 and len(cat_vars) == 1:
                        num_var, cat_var = num_vars[0], cat_vars[0]
                        if df[cat_var].nunique() < 10: # 限制类别的数量以保持图表清晰
                            fig, ax = plt.subplots(figsize=(10, 7))
                            sns.scatterplot(x=num_var, y=tgt, hue=cat_var, data=df, ax=ax, palette="deep")
                            ax.set_title(f"'{tgt}' vs '{num_var}', colored by '{cat_var}'")
                            viz_title = f"Interaction Plot: ({num_var}, {cat_var}) -> {tgt}"
                            visualizations[viz_title] = fig
                            plt.close(fig)

        except Exception as e:
            print(f"Could not create visualization for relationship {edge}: {e}")

    return visualizations
