import pandas as pd
from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

# Load and prepare data using session
def load_failure_data(session: Session):
    try:
        query = """
            SELECT sr.replacement_id, sr.reason, sr.vehicle_id, v.vehicle_number
            FROM spare_replacement sr
            JOIN vehicle v ON sr.vehicle_id = v.vehicle_id
        """
        df = pd.read_sql(query, session.bind).dropna()

        # Create a dictionary of replacement_id -> reason
        replacement_dict = df[['replacement_id', 'reason']].drop_duplicates().set_index('replacement_id')['reason'].to_dict()
        return df, replacement_dict
    except Exception as e:
        print(f"Error loading failure data: {str(e)}")
        return pd.DataFrame(), {}

# Dynamic clustering with optimal silhouette score
def cluster_failure_reasons(filtered_df):
    vectorizer = TfidfVectorizer(stop_words='english')
    X = vectorizer.fit_transform(filtered_df['reason'])

    best_score = -1
    best_k = 2
    best_labels = None
    best_model = None

    for k in range(2, min(10, len(filtered_df))):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(X)
        score = silhouette_score(X, labels)

        if score > best_score:
            best_score = score
            best_k = k
            best_labels = labels
            best_model = kmeans

    filtered_df.loc[:, 'cluster'] = best_labels  # Using .loc to avoid the warning

    cluster_data = []
    for cluster_num in range(best_k):
        cluster_issues = filtered_df[filtered_df['cluster'] == cluster_num]['reason'].value_counts()
        cluster_data.append({
            "cluster": cluster_num,
            "cluster_size": int(cluster_issues.sum()),
            "highlight": cluster_issues.idxmax()
        })

    return cluster_data, best_score, filtered_df

# Predict spare failures using Apriori
def get_association_rules(filtered_df, replacement_dict, clusters=False):
    grouped = filtered_df.groupby('replacement_id').agg(list)
    transactions = grouped['reason'].apply(lambda x: list(set(x))).tolist()

    if not transactions or len(transactions) < 2:
        return []

    te = TransactionEncoder()
    te_ary = te.fit(transactions).transform(transactions)
    df_te = pd.DataFrame(te_ary, columns=te.columns_)

    frequent_itemsets = apriori(df_te, min_support=0.01, use_colnames=True)
    if frequent_itemsets.empty:
        return []

    rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.0)
    if rules.empty:
        return []

    result = rules[['antecedents', 'consequents', 'support', 'confidence', 'lift']].sort_values(by='lift', ascending=False)

    def map_replacement_to_reason(items):
        return [replacement_dict.get(item, item) for item in items]

    result['consequents'] = result['consequents'].apply(lambda x: map_replacement_to_reason(list(x)))
    predicted_spares = result['consequents'].apply(lambda x: ', '.join(x)).tolist()

    # Optionally, modify predictions based on clusters
    if clusters:
        # Merge predictions with clusters to improve context-aware results
        cluster_predictions = []
        for cluster in filtered_df['cluster'].unique():
            cluster_df = filtered_df[filtered_df['cluster'] == cluster]
            cluster_rules = get_association_rules(cluster_df, replacement_dict)
            cluster_predictions.append((cluster, cluster_rules))
        return cluster_predictions

    return predicted_spares[:3]  # Limit to top 3
