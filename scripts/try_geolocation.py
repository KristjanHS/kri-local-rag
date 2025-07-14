import streamlit as st
from streamlit_geolocation import streamlit_geolocation

loc = streamlit_geolocation()
st.write(loc)
