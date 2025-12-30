import streamlit as st
import pandas as pd
import numpy as np

# Set page configuration
st.set_page_config(
    page_title="Put Side Strategy Dashboard",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and Introduction
st.title("📉 Put Side Entry & Exit Strategy Dashboard")
st.markdown("""
This dashboard digitizes the multi-timeframe Put Side strategy. 
Use the tabs below to review rules, check active entry signals, or calculate exit conditions.
""")

# --- SECTION 1: DATA PREPARATION (DIGITIZING THE IMAGE) ---

# Entry Conditions Data
entry_data = {
    "Indicators": [
        "BB (60)", "BB (105)", "BB (150)", 
        "Williams % R(28)", "RSI (20)", 
        "DMI (6, 6) Rules", "DMI (20, 20) Rules"
    ],
    "2 HOURS": [
        "-", "-", "-", 
        "-80 to -100", "40 to 1", 
        "-", "-"
    ],
    "10 MINUTES": [
        "≤ 35%", "Show Value", "Show Value", 
        "-80 to -100", "40 to 1", 
        "-DI ≥ 35 and +DI ≤ 15", 
        "-DI ≥ 30 and +DI ≤ 15"
    ],
    "2 MINUTES": [
        "Show Value", "Show Value", "Show Value", 
        "-", "-", 
        "-DI ≥ 35 and +DI ≤ 15", 
        "-DI ≥ 30 and +DI ≤ 15"
    ]
}

# Exit Conditions Data
exit_data = {
    "Indicators": ["DMI (20, 20)", "Moving average (8)"],
    "2 HOURS": ["-", "-"],
    "10 MINUTES": ["-", "It should cross (8)"],
    "2 MINUTES": ["Difference of Upper (+DI) & Lower (-DI) values should be < 10", "-"]
}

df_entry_rules = pd.DataFrame(entry_data)
df_exit_rules = pd.DataFrame(exit_data)


# --- SECTION 2: STREAMLIT INTERFACE CONSTRUCTION ---

# Create main tabs
tab_rules, tab_entry, tab_exit = st.tabs(["📋 Strategy Reference Tables", "⚡ Interactive Entry Signal Checker", "🚪 Exit Condition Calculators"])

# ===========================
# TAB 1: STRATEGY REFERENCE
# ===========================
with tab_rules:
    st.subheader("Put Side Entry Conditions Table")
    st.table(df_entry_rules)
    
    st.divider()
    
    st.subheader("Exit Conditions Table")
    st.table(df_exit_rules)
    st.info("Note: For DMI entries in the image, it listed '-DI' twice for the thresholds. Standard bearish practice interprets this as Negative DI (-DI) being high and Positive DI (+DI) being low. The tables above reflect this logical interpretation.")

# ===========================
# TAB 2: ENTRY SIGNAL CHECKER
# ===========================
with tab_entry:
    st.subheader("Analyze Current Market Conditions for Entry")
    
    # Sidebar for Timeframe Selection
    with st.sidebar:
        st.header("Signal Settings")
        selected_tf = st.radio("Select Active Timeframe:", ["2 HOURS", "10 MINUTES", "2 MINUTES"])
        st.markdown("---")
        st.markdown("**Instructions:** Select the timeframe you are analyzing on your chart, enter the current indicator values in the main window, and click 'Check Signals'.")

    st.write(f"### Analyzing Timeframe: **{selected_tf}**")
    
    # --- INPUTS (Conditional based on TF selection) ---
    col1, col2, col3 = st.columns(3)
    
    # Initialize variables to None so we know if they were used
    wr_input = rsi_input = bb60_input = None
    dmi6_neg = dmi6_pos = dmi20_neg = dmi20_pos = None

    with col1:
        st.markdown("#### Momentum Indicators")
        if selected_tf in ["2 HOURS", "10 MINUTES"]:
            wr_input = st.number_input("Williams % R(28) Value", min_value=-100.0, max_value=0.0, value=-50.0, step=1.0)
            rsi_input = st.number_input("RSI (20) Value", min_value=0.0, max_value=100.0, value=50.0, step=1.0)
        else:
            st.markdown("*Not applicable for 2 Minutes timeframe.*")
            
    with col2:
        st.markdown("#### Volatility / Bands")
        if selected_tf == "10 MINUTES":
             bb60_input = st.number_input("BB (60) Percentage Value", value=40.0, help="Enter the percentage value as defined by your charting platform for the ≤35% rule.")
        else:
             st.markdown("*Specific BB thresholds not defined for this timeframe (Show Value only).*")

    with col3:
        st.markdown("#### DMI / Trend Strength")
        if selected_tf in ["10 MINUTES", "2 MINUTES"]:
            st.caption("DMI (6, 6) Inputs")
            dmi6_neg = st.number_input("DMI(6,6) Negative DI (-DI)", value=20.0)
            dmi6_pos = st.number_input("DMI(6,6) Positive DI (+DI)", value=20.0)
            st.divider()
            st.caption("DMI (20, 20) Inputs")
            dmi20_neg = st.number_input("DMI(20,20) Negative DI (-DI)", value=20.0)
            dmi20_pos = st.number_input("DMI(20,20) Positive DI (+DI)", value=20.0)
        else:
            st.markdown("*DMI conditions not applicable for 2 Hours timeframe.*")

    st.divider()

    # --- LOGIC PROCESSOR ---
    if st.button("✅ Check Entry Signals Now", type="primary"):
        st.subheader("Signal Analysis Results")
        check_list = []
        all_conditions_met = True
        
        # --- 2 HOURS LOGIC ---
        if selected_tf == "2 HOURS":
            # WR Check
            if -100 <= wr_input <= -80:
                check_list.append("✅ **Williams %R(28):** Bearish range (-80 to -100) met.")
            else:
                check_list.append(f"❌ **Williams %R(28):** Current value ({wr_input}) is outside required range.")
                all_conditions_met = False
            
            # RSI Check
            if 1 <= rsi_input <= 40:
                 check_list.append("✅ **RSI(20):** Bearish range (1 to 40) met.")
            else:
                 check_list.append(f"❌ **RSI(20):** Current value ({rsi_input}) is outside required range.")
                 all_conditions_met = False

        # --- 10 MINUTES LOGIC ---
        elif selected_tf == "10 MINUTES":
            # BB(60) Check
            if bb60_input <= 35:
                 check_list.append(f"✅ **BB(60):** Value ({bb60_input}%) is ≤ 35%.")
            else:
                 check_list.append(f"❌ **BB(60):** Value ({bb60_input}%) is > 35%.")
                 all_conditions_met = False
                 
            # WR Check
            if -100 <= wr_input <= -80:
                check_list.append("✅ **Williams %R(28):** Bearish range met.")
            else:
                check_list.append("❌ **Williams %R(28):** Not in bearish range.")
                all_conditions_met = False

            # RSI Check
            if 1 <= rsi_input <= 40:
                 check_list.append("✅ **RSI(20):** Bearish range met.")
            else:
                 check_list.append("❌ **RSI(20):** Not in bearish range.")
                 all_conditions_met = False
            
            # DMI (6,6) Check (-DI >= 35 AND +DI <= 15)
            if dmi6_neg >= 35 and dmi6_pos <= 15:
                 check_list.append("✅ **DMI(6,6):** Strong bearish trend conditions met.")
            else:
                 check_list.append(f"❌ **DMI(6,6):** Conditions not met. (Need -DI≥35, +DI≤15. Got -DI:{dmi6_neg}, +DI:{dmi6_pos})")
                 all_conditions_met = False

            # DMI (20,20) Check (-DI >= 30 AND +DI <= 15)
            if dmi20_neg >= 30 and dmi20_pos <= 15:
                 check_list.append("✅ **DMI(20,20):** Strong bearish trend conditions met.")
            else:
                 check_list.append(f"❌ **DMI(20,20):** Conditions not met. (Need -DI≥30, +DI≤15. Got -DI:{dmi20_neg}, +DI:{dmi20_pos})")
                 all_conditions_met = False

        # --- 2 MINUTES LOGIC ---
        elif selected_tf == "2 MINUTES":
             # DMI (6,6) Check (-DI >= 35 AND +DI <= 15)
            if dmi6_neg >= 35 and dmi6_pos <= 15:
                 check_list.append("✅ **DMI(6,6):** Strong bearish trend conditions met.")
            else:
                 check_list.append(f"❌ **DMI(6,6):** Conditions not met. (Need -DI≥35, +DI≤15. Got -DI:{dmi6_neg}, +DI:{dmi6_pos})")
                 all_conditions_met = False

            # DMI (20,20) Check (-DI >= 30 AND +DI <= 15)
            if dmi20_neg >= 30 and dmi20_pos <= 15:
                 check_list.append("✅ **DMI(20,20):** Strong bearish trend conditions met.")
            else:
                 check_list.append(f"❌ **DMI(20,20):** Conditions not met. (Need -DI≥30, +DI≤15. Got -DI:{dmi20_neg}, +DI:{dmi20_pos})")
                 all_conditions_met = False

        # --- FINAL OUTPUT ---
        for item in check_list:
            st.markdown(item)

        st.markdown("---")
        if all_conditions_met:
            st.success(f"🎉 ENTRY SIGNAL CONFIRMED on the {selected_tf} timeframe! All specific criteria are met.")
        else:
            st.error(f"⛔ ENTRY SIGNAL FAILED. Some conditions on the {selected_tf} timeframe were not met.")

# ===========================
# TAB 3: EXIT CONDITION CALCULATORS
# ===========================
with tab_exit:
    st.subheader("Exit Signal Calculators")
    st.markdown("Use these tools to check if specific exit conditions specified in the strategy are met.")

    col_exit1, col_exit2 = st.columns(2)

    # --- 2 MINUTE EXIT CALCULATOR ---
    with col_exit1:
        st.markdown("### ⏱️ 2-Minute Exit (DMI Contraction)")
        st.info("Rule: Exit if difference between DMI (20,20) Upper (+DI) and Lower (-DI) values is below 10.")
        
        exit_dmi_pos = st.number_input("Enter current +DI (Positive) Value:", value=25.0, key="exit_pos")
        exit_dmi_neg = st.number_input("Enter current -DI (Negative) Value:", value=18.0, key="exit_neg")
        
        if st.button("Calculate DMI Difference"):
            diff = abs(exit_dmi_pos - exit_dmi_neg)
            st.metric("DMI Difference", f"{diff:.2f}")
            
            if diff < 10:
                st.error("⚠️ EXIT SIGNAL: Difference is below 10. Consider exiting Put position.")
            else:
                st.success("✅ HOLD SIGNAL: Difference is 10 or higher. Trend strength still present.")

    # --- 10 MINUTE EXIT CHECKER ---
    with col_exit2:
        st.markdown("### ⏱️ 10-Minute Exit (MA Cross)")
        st.info("Rule: Exit when Price crosses the 8-period Moving Average.")
        
        st.write("This is a visual check on your chart. However, you can input values here to confirm a cross.")
        
        ma8_val = st.number_input("Current Moving Average (8) Value:", value=100.00, format="%.2f")
        current_price = st.number_input("Current Asset Price:", value=99.00, format="%.2f")
        
        previous_price = st.number_input("(Optional) Previous Candle Close Price:", value=101.00, format="%.2f", help="Helps determine if a cross actually happened recently.")

        if st.button("Check MA Cross"):
            st.markdown(f"**Analysis:** Price: {current_price} | MA(8): {ma8_val}")

            # Simple check: Price is now above MA in a Put trade
            if current_price > ma8_val:
                 st.error("⚠️ EXIT WARNING: Current price is ABOVE the 8 MA.")
                 
                 # More complex check if previous price is provided
                 if previous_price is not None:
                    if previous_price <= ma8_val and current_price > ma8_val:
                        st.error("⚠️ EXIT SIGNAL CONFIRMED: Price has actively CROSSED UP over the 8 MA.")
            else:
                 st.success("✅ HOLD SIGNAL: Price remains below the 8 MA.")