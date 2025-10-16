from pathlib import Path
import pandas as pd
import plotly.graph_objects as go


csvpath = Path(__file__).parent / "sankey.csv"
df = pd.read_csv(csvpath)

# fmt:off
doc_chunks          = df["doc chunks"].sum()
linux_chunks        = df[df["kernel"] == "Linux"]["doc chunks"].sum()
linux_kmr           = df[df["kernel"] == "Linux"]["KMR"].sum()
linux_ekmr          = df[df["kernel"] == "Linux"]["EKMR"].sum()
linux_hq            = df[df["kernel"] == "Linux"]["EKMR-high-quality"].sum()
linux_lq_nocov      = df[df["kernel"] == "Linux"]["EKMR-low-quality-nocov"].sum()
linux_lq_highvio    = df[df["kernel"] == "Linux"]["EKMR-low-quality-highvio"].sum()
android_chunks      = df[df["kernel"] == "Android"]["doc chunks"].sum()
android_kmr         = df[df["kernel"] == "Android"]["KMR"].sum()
android_ekmr        = df[df["kernel"] == "Android"]["EKMR"].sum()
android_hq          = df[df["kernel"] == "Android"]["EKMR-high-quality"].sum()
android_lq_nocov    = df[df["kernel"] == "Android"]["EKMR-low-quality-nocov"].sum()
android_lq_highvio  = df[df["kernel"] == "Android"]["EKMR-low-quality-highvio"].sum()
# fmt:on

# Document Chunks -> Linux/Android -> KMR/No Consensus -> EKMR/Generation Failed -> High-Quality/Low-Quality (nocov/highvio) EKMRs
data = dict(
    node_labels=[
        "Document Chunks",
        "Linux",
        "Android",
        "KMR",
        "No Consensus",
        "EKMR",
        "Generation Failed",
        "High-Quality EKMRs",
        "Low-Quality EKMRs<br>(No Coverage)",
        "Low-Quality EKMRs<br>(High Violation Rate)",
    ],
    node_colors=[
        "purple",
        "rgba(0,114,178,0.6)",
        "rgba(0,158,115,0.6)",
        "rgba(0,114,178,0.8)",
        "rgba(0,114,178,0.8)",
        "rgba(0,114,178,0.8)",
        "rgba(0,114,178,0.8)",
        "rgba(0,114,178,0.8)",
        "rgba(0,114,178,0.8)",
        "rgba(0,114,178,0.8)",
    ],
    node_xs=[0.1, 0.3, 0.3, 0.5, 0.5, 0.7, 0.7, 0.9, 0.9, 0.9],
    node_ys=[0.5, 0.25, 0.8, 0.45, 0.9, 0.45, 0.85, 0.3, 0.7, 0.95],
    link_sources=[0, 0, 1, 1, 2, 2, 3, 3, 3, 3, 5, 5, 5, 5, 5, 5],  # oh shit
    link_targets=[1, 2, 3, 4, 3, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9],
    link_values=[
        linux_chunks,
        android_chunks,
        linux_kmr,
        linux_chunks - linux_kmr,
        android_kmr,
        android_chunks - android_kmr,
        linux_ekmr,
        android_ekmr,
        linux_kmr - linux_ekmr,
        android_kmr - android_ekmr,
        linux_hq,
        android_hq,
        linux_lq_nocov,
        android_lq_nocov,
        linux_lq_highvio,
        android_lq_highvio,
    ],
    link_colors=["rgba(0,114,178,0.4)", "rgba(0,158,115,0.4)"] * 8,
)

fig = go.Figure(
    data=go.Sankey(
        node=dict(
            pad=15,
            thickness=15,
            line=dict(color="black", width=0.5),
            label=data["node_labels"],
            color=data["node_colors"],
            x=data["node_xs"],
            y=data["node_ys"],
        ),
        link=dict(
            source=data["link_sources"],
            target=data["link_targets"],
            value=data["link_values"],
            color=data["link_colors"],
        ),
    )
)

fig.update_layout(
    width=800,
    height=400,
    margin=dict(l=10, r=10, t=10, b=10),
)

outdir = Path(__file__).parent / "output"
outdir.mkdir(exist_ok=True)
fig.write_html(outdir / "sankey.html")
fig.write_image(outdir / "sankey.png", scale=2)
fig.write_image(outdir / "sankey.pdf", scale=2)

print(f"Sankey figure saved to {outdir}")
