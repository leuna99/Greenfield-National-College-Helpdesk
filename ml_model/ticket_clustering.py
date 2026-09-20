import sqlite3
import pandas as pd
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans


# =========================================================
# DATABASE
# =========================================================

DB_PATH = "../helpdesk.db"

connection = sqlite3.connect(DB_PATH)

query = """
SELECT id, subject, description
FROM tickets
WHERE description IS NOT NULL
AND TRIM(description) != ''
"""

tickets = pd.read_sql_query(query, connection)

connection.close()


# =========================================================
# CHECK TICKET COUNT
# =========================================================

if len(tickets) < 2:

    print("\n===================================")
    print("STUDENT TICKET CLUSTERING")
    print("===================================")

    print("\nNot enough tickets for clustering.")
    print("At least 2 tickets are required.")

    exit()


print("\n===================================")
print("STUDENT TICKET CLUSTERING")
print("===================================")

print(f"\nTotal tickets found: {len(tickets)}")


# =========================================================
# COMBINE SUBJECT + DESCRIPTION
# =========================================================

tickets["text"] = (
    tickets["subject"].fillna("") + " " +
    tickets["description"].fillna("")
)


# =========================================================
# TF-IDF FEATURE EXTRACTION
# =========================================================

vectorizer = TfidfVectorizer(
    lowercase=True,
    stop_words="english",
    ngram_range=(1, 2)
)

X = vectorizer.fit_transform(
    tickets["text"]
)


# =========================================================
# FIND DISTINCT DATA POINTS
# =========================================================

total_tickets = len(tickets)

unique_vectors = np.unique(
    X.toarray(),
    axis=0
).shape[0]

print(f"Distinct ticket patterns: {unique_vectors}")


# =========================================================
# AUTOMATIC CLUSTER SELECTION
# =========================================================

if unique_vectors < 2:

    best_k = 1

else:

    max_k = min(
        10,
        total_tickets,
        unique_vectors
    )

    if max_k == 2:

        best_k = 2

    else:

        inertias = []

        print("\nTesting possible cluster numbers...")
        print("-----------------------------------")

        for k in range(2, max_k + 1):

            model = KMeans(
                n_clusters=k,
                random_state=42,
                n_init=10
            )

            model.fit(X)

            inertias.append(
                model.inertia_
            )

            print(
                f"K = {k}  "
                f"Inertia = {model.inertia_:.4f}"
            )


        # -------------------------------------------------
        # Calculate improvement between K values
        # -------------------------------------------------

        improvements = []

        for i in range(1, len(inertias)):

            improvement = (
                inertias[i - 1] -
                inertias[i]
            )

            improvements.append(
                improvement
            )


        # -------------------------------------------------
        # Select elbow automatically
        # -------------------------------------------------

        if len(improvements) == 1:

            best_k = 2

        else:

            ratios = []

            for i in range(1, len(improvements)):

                previous = improvements[i - 1]
                current = improvements[i]

                if previous == 0:

                    ratio = 1

                else:

                    ratio = current / previous

                ratios.append(ratio)


            best_index = ratios.index(
                min(ratios)
            ) + 1

            best_k = best_index + 2


        # -------------------------------------------------
        # Final safety check
        # -------------------------------------------------

        best_k = min(
            best_k,
            unique_vectors,
            total_tickets
        )


# =========================================================
# DISPLAY SELECTED NUMBER
# =========================================================

print("\n===================================")
print("AUTOMATIC CLUSTER SELECTION")
print("===================================")

print(
    f"Selected number of clusters: {best_k}"
)


# =========================================================
# K-MEANS CLUSTERING
# =========================================================

kmeans = KMeans(
    n_clusters=best_k,
    random_state=42,
    n_init=10
)

tickets["cluster"] = kmeans.fit_predict(X)


# =========================================================
# CLUSTER COUNTS
# =========================================================

cluster_counts = (
    tickets["cluster"]
    .value_counts()
    .sort_values(
        ascending=False
    )
)


print("\n===================================")
print("CLUSTER RESULTS")
print("===================================")


for cluster, count in cluster_counts.items():

    print(
        f"Cluster {cluster + 1}: "
        f"{count} tickets"
    )


# =========================================================
# TICKET GROUPS
# =========================================================

print("\n===================================")
print("TICKET GROUPS")
print("===================================")


for cluster in cluster_counts.index:

    print(
        f"\nCluster {cluster + 1}"
    )

    cluster_tickets = tickets[
        tickets["cluster"] == cluster
    ]


    for _, ticket in cluster_tickets.iterrows():

        print(
            f"- Ticket #{ticket['id']}: "
            f"{ticket['subject']}"
        )


# =========================================================
# MOST REPORTED ISSUE
# =========================================================

largest_cluster = cluster_counts.index[0]

largest_count = cluster_counts.iloc[0]

largest_tickets = tickets[
    tickets["cluster"] == largest_cluster
]


most_common_subject = (
    largest_tickets["subject"]
    .value_counts()
    .index[0]
)


print("\n===================================")
print("MOST REPORTED ISSUE GROUP")
print("===================================")

print(
    f"Issue: {most_common_subject}"
)

print(
    f"Tickets: {largest_count}"
)


# =========================================================
# FINAL RESULT
# =========================================================

print("\n===================================")
print("CLUSTERING COMPLETED")
print("===================================")

print(
    f"Total tickets: {total_tickets}"
)

print(
    f"Detected groups: {best_k}"
)

print(
    f"Most reported issue: "
    f"{most_common_subject}"
)

print(
    f"Number of tickets in largest group: "
    f"{largest_count}"
)

print("\nClustering completed successfully.")