import matplotlib.patches as patches
import matplotlib.pyplot as plt

# Set up the figure with a clean, academic style
fig, ax = plt.subplots(1, 1, figsize=(14, 8))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")

# Define colors - professional palette
color_weak = "#E8F4F8"
color_semi = "#B3D9E8"
color_strong = "#7FB3D5"
border_color = "#2C3E50"
text_color = "#2C3E50"

# Create nested rectangles representing the three forms
# Strong form (outermost)
strong_rect = patches.FancyBboxPatch(
    (0.5, 1.5),
    9,
    7,
    boxstyle="round,pad=0.1",
    linewidth=3,
    edgecolor=border_color,
    facecolor=color_strong,
    alpha=0.7,
)
ax.add_patch(strong_rect)

# Semi-strong form (middle)
semi_rect = patches.FancyBboxPatch(
    (1.5, 2.5),
    7,
    5,
    boxstyle="round,pad=0.1",
    linewidth=3,
    edgecolor=border_color,
    facecolor=color_semi,
    alpha=0.8,
)
ax.add_patch(semi_rect)

# Weak form (innermost)
weak_rect = patches.FancyBboxPatch(
    (2.5, 3.5),
    5,
    3,
    boxstyle="round,pad=0.1",
    linewidth=3,
    edgecolor=border_color,
    facecolor=color_weak,
    alpha=0.9,
)
ax.add_patch(weak_rect)

# Add labels for each form
ax.text(
    5,
    5,
    "WEAK FORM",
    fontsize=24,
    fontweight="bold",
    ha="center",
    va="center",
    color=text_color,
)

ax.text(
    5,
    7,
    "SEMI-STRONG FORM",
    fontsize=24,
    fontweight="bold",
    ha="center",
    va="center",
    color=text_color,
)

ax.text(
    5,
    8.7,
    "STRONG FORM",
    fontsize=24,
    fontweight="bold",
    ha="center",
    va="center",
    color=text_color,
)

# Add information content descriptions
# Weak form
ax.text(
    5,
    4.3,
    "Past prices, accounting, & trading volume",
    fontsize=14,
    ha="center",
    va="center",
    color=text_color,
    style="italic",
)

# Semi-strong form
ax.text(
    1.5,
    6,
    "Public news:",
    fontsize=12,
    ha="left",
    va="center",
    color=text_color,
    fontweight="bold",
)
ax.text(
    1.5, 5.1, "•Earnings news", fontsize=11, ha="left", va="center", color=text_color
)

ax.text(1.5, 4.7, "•SEC filings", fontsize=11, ha="left", va="center", color=text_color)
ax.text(
    1.5, 4.3, "•Press releases", fontsize=11, ha="left", va="center", color=text_color
)

# Strong form
ax.text(
    0.7,
    2.0,
    "Private (Insider) Information",
    fontsize=12,
    ha="left",
    va="center",
    color=text_color,
    fontweight="bold",
    style="italic",
)

# Add arrows and implications
ax.annotate(
    "",
    xy=(0.3, 3.5),
    xytext=(0.3, 5.5),
    arrowprops=dict(arrowstyle="<->", color=text_color, lw=2),
)


# Add title
fig.suptitle(
    "Three Forms of Market Efficiency",
    fontsize=28,
    fontweight="bold",
    y=0.98,
    color=text_color,
)

plt.tight_layout()
plt.savefig(
    "/Users/charles.martineau/Dropbox/Github/MGFD40/lecture04/figures/market_efficiency_forms.png",
    dpi=300,
    bbox_inches="tight",
    facecolor="white",
)
print("Figure saved successfully!")
