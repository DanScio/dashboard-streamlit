import streamlit as st
import pandas as pd
import plotly.express as px
import os
ADMIN_CODE = st.secrets.get("ADMIN_CODE", "")
print(ADMIN_CODE)