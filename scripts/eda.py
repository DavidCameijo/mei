import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description='Generate EDA tables and plots from merged results CSV')
    parser.add_argument('--input', default='output/merged_results.csv')
    parser.add_argument('--outdir', default='output/figures')
    args = parser.parse_args()

    ensure_dir(args.outdir)

    df = pd.read_csv(args.input)

    # normalize columns
    for c in ['passed', 'tests_passed', 'tests_total', 'tests_passed_pct', 'loc', 'cyclomatic_complexity']:
        if c in df.columns:
            df[c] = df[c].apply(lambda v: safe_float(v) if pd.notna(v) else None)

    # convert passed to numeric (1/0) robustly
    def to_passed_flag(v):
        if pd.isna(v):
            return None
        if isinstance(v, (int, float)):
            return 1 if v == 1 else 0 if v == 0 else None
        s = str(v).strip().lower()
        if s in ('true','t','yes','y','1'):
            return 1
        if s in ('false','f','no','n','0'):
            return 0
        return None

    if 'passed' in df.columns:
        df['passed_flag'] = df['passed'].apply(to_passed_flag)

    # Summary table: per-llm counts and success rate
    grp = df.groupby('llm')
    summary = grp.agg(
        problems_evaluated=('problem_id','nunique'),
        solutions_evaluated=('passed_flag','count'),
        success_rate=('passed_flag','mean')
    ).reset_index()
    summary['success_rate'] = (summary['success_rate'].fillna(0) * 100).round(3)
    summary.to_csv(os.path.join(args.outdir, 'summary_by_llm.csv'), index=False)

    # Also summary by llm x difficulty
    if 'difficulty' in df.columns:
        sd = df.groupby(['llm','difficulty']).agg(
            problems_evaluated=('problem_id','nunique'),
            solutions_evaluated=('passed_flag','count'),
            success_rate=('passed_flag','mean')
        ).reset_index()
        sd['success_rate'] = (sd['success_rate'] * 100).round(3)
        sd.to_csv(os.path.join(args.outdir, 'summary_by_llm_difficulty.csv'), index=False)

        difficulty_order = ['Easy', 'Medium', 'Hard']
        present_order = [d for d in difficulty_order if d in set(sd['difficulty'])]
        sd_plot = sd.copy()
        sd_plot['difficulty'] = pd.Categorical(sd_plot['difficulty'], categories=present_order, ordered=True)
        sd_plot = sd_plot.sort_values(['difficulty', 'llm'])

        plt.figure(figsize=(9, 5))
        ax = sns.barplot(
            data=sd_plot,
            x='difficulty',
            y='success_rate',
            hue='llm',
            palette='Set2'
        )
        ax.set_ylabel('Code correctness / success rate (%)')
        ax.set_xlabel('Task difficulty')
        ax.set_ylim(0, 100)
        for container in ax.containers:
            ax.bar_label(container, fmt='%.1f', padding=2, fontsize=8)
        plt.legend(title='LLM', loc='best')
        plt.tight_layout()
        plt.savefig(os.path.join(args.outdir, 'success_rate_by_difficulty_and_llm.png'), dpi=200)
        plt.close()

        # Alternate view: line plot for easier comparison across the 3 difficulty levels
        plt.figure(figsize=(9, 5))
        ax = sns.lineplot(
            data=sd_plot,
            x='difficulty',
            y='success_rate',
            hue='llm',
            marker='o',
            linewidth=2.2,
            palette='Set2'
        )
        ax.set_ylabel('Code correctness / success rate (%)')
        ax.set_xlabel('Task difficulty')
        ax.set_ylim(0, 100)
        plt.legend(title='LLM', loc='best')
        plt.tight_layout()
        plt.savefig(os.path.join(args.outdir, 'success_rate_by_difficulty_and_llm_line.png'), dpi=200)
        plt.close()

    sns.set(style='whitegrid')

    # Bar chart: success rate per model
    plt.figure(figsize=(8,4))
    ax = sns.barplot(data=summary.sort_values('success_rate', ascending=False), x='llm', y='success_rate', palette='muted')
    ax.set_ylabel('Success rate (%)')
    ax.set_xlabel('LLM')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(args.outdir, 'success_rate_by_llm.png'), dpi=200)
    plt.close()

    # Boxplots: LOC and cyclomatic complexity per model
    for col in ['loc', 'cyclomatic_complexity']:
        if col in df.columns:
            plt.figure(figsize=(8,4))
            sns.boxplot(data=df, x='llm', y=col, palette='Set2')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            fname = f'{col}_by_llm_boxplot.png'
            plt.savefig(os.path.join(args.outdir, fname), dpi=200)
            plt.close()

    # Test correctness percentage: normalize and plot
    if 'tests_passed_pct' in df.columns:
        # normalize to 0-100 scale if values are 0-1
        def normalize_pct(v):
            try:
                if pd.isna(v):
                    return None
                f = float(v)
                if f <= 1.0:
                    return f * 100.0
                return f
            except Exception:
                return None

        df['tests_passed_pct_norm'] = df['tests_passed_pct'].apply(normalize_pct)

        # boxplot by llm
        plt.figure(figsize=(8,4))
        sns.boxplot(data=df, x='llm', y='tests_passed_pct_norm', palette='cool')
        plt.ylabel('Tests passed (%)')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(args.outdir, 'tests_passed_pct_by_llm_boxplot.png'), dpi=200)
        plt.close()

        # average tests_passed_pct per llm (vertical bar and horizontal annotated bar)
        avg_pct = df.groupby('llm')['tests_passed_pct_norm'].mean().reset_index()
        avg_pct['tests_passed_pct_norm'] = avg_pct['tests_passed_pct_norm'].round(3)
        plt.figure(figsize=(8,4))
        sns.barplot(data=avg_pct.sort_values('tests_passed_pct_norm', ascending=False), x='llm', y='tests_passed_pct_norm', palette='muted')
        plt.ylabel('Average tests passed (%)')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(args.outdir, 'avg_tests_passed_pct_by_llm.png'), dpi=200)
        plt.close()

        # Horizontal bar with annotations for visibility
        avg_pct_h = avg_pct.sort_values('tests_passed_pct_norm', ascending=True)
        plt.figure(figsize=(8, max(3, 0.6 * len(avg_pct_h))))
        ax = sns.barplot(data=avg_pct_h, x='tests_passed_pct_norm', y='llm', palette='crest')
        ax.set_xlabel('Average tests passed (%)')
        ax.set_ylabel('LLM')
        for p in ax.patches:
            w = p.get_width()
            ax.annotate(f"{w:.1f}%", (w + 0.5, p.get_y() + p.get_height() / 2.), va='center')
        plt.tight_layout()
        plt.savefig(os.path.join(args.outdir, 'avg_tests_passed_pct_by_llm_hbar.png'), dpi=200)
        plt.close()

        # Violin + swarm for distribution visibility
        plt.figure(figsize=(10,5))
        sns.violinplot(data=df, x='llm', y='tests_passed_pct_norm', inner=None, palette='Pastel1')
        sns.swarmplot(data=df, x='llm', y='tests_passed_pct_norm', color='k', size=3)
        plt.ylabel('Tests passed (%)')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(args.outdir, 'tests_passed_pct_violin_swarm.png'), dpi=200)
        plt.close()

    # Pass/Fail counts per llm
    if 'passed_flag' in df.columns:
        counts = df.groupby('llm')['passed_flag'].agg(['sum','count']).reset_index()
        counts['fail'] = counts['count'] - counts['sum']
        counts = counts.sort_values('sum', ascending=False)
        plt.figure(figsize=(8,4))
        # stacked bar: absolute counts
        plt.bar(counts['llm'], counts['sum'], label='passed', color='#2ca02c')
        plt.bar(counts['llm'], counts['fail'], bottom=counts['sum'], label='failed', color='#d62728')
        plt.ylabel('Number of solutions')
        plt.xticks(rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(args.outdir, 'pass_fail_counts_by_llm.png'), dpi=200)
        plt.close()

        # percent-stacked bar for passed vs failed
        pct = counts.set_index('llm')[['sum','fail']]
        pct = pct.div(pct.sum(axis=1), axis=0) * 100
        pct = pct.rename(columns={'sum':'passed_pct','fail':'failed_pct'})
        plt.figure(figsize=(8,4))
        pct[['passed_pct','failed_pct']].plot(kind='bar', stacked=True, color=['#2ca02c','#d62728'])
        plt.ylabel('Percent of solutions')
        plt.xlabel('LLM')
        plt.xticks(rotation=45, ha='right')
        plt.legend(loc='upper right')
        plt.tight_layout()
        plt.savefig(os.path.join(args.outdir, 'pass_fail_percent_stacked_by_llm.png'), dpi=200)
        plt.close()

    # Optional: boxplots by difficulty
    if 'difficulty' in df.columns:
        for col in ['loc', 'cyclomatic_complexity']:
            if col in df.columns:
                plt.figure(figsize=(10,5))
                sns.boxplot(data=df, x='difficulty', y=col, hue='llm')
                plt.xticks(rotation=0)
                plt.tight_layout()
                fname = f'{col}_by_difficulty_boxplot.png'
                plt.savefig(os.path.join(args.outdir, fname), dpi=200)
                plt.close()

    print('EDA complete — summary and figures written to', args.outdir)


if __name__ == '__main__':
    main()
