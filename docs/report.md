# PREDICTING AIR POLLUTION LEVELS IN MALAYSIA USING REAL TIME WEB DATA

---

## Declaration of Thesis Confidentiality

**Author's full name:** BRYAN QUINN DARLEN
**IC No./Passport No.:** E0612326
**Thesis/Project title:** PREDICTING AIR POLLUTION LEVELS IN MALAYSIA USING REAL TIME WEB DATA

I declare that this thesis is classified as:

- [ ] CONFIDENTIAL
- [ ] RESTRICTED
- [x] OPEN ACCESS

I acknowledged that Asia Pacific University of Technology & Innovation (APU) reserves the right as follows:

1. The thesis is the property of Asia Pacific University of Technology & Innovation (APU).
2. The Library of Asia Pacific University of Technology & Innovation (APU) has the right to make copies for the purpose of research only.
3. The Library has the right to make copies of the thesis for academic exchange.

**Author's Signature:**

**Date:** 27 February 2025

---

**Supervisor's Name:** DR. PREETHI SUBRAMANIAN

**Date:** 27 July 2025

**Signature:** …………S. Preethi…………………

---

## Acknowledgement

In this page, the researcher would like to use this opportunity to express profound gratitude to everyone who contributed to the completion of this project. First and foremost, thanks to God Almighty for His blessings. Therefore, heartfelt thanks to Dr. Preethi Subramanian as the supervisor of the researcher, who supported the research from beginning.

I also want to convey my appreciation to my family, especially my parents, for their constant support and help that kept me going during moments of difficulty.

Lastly, I am grateful to my friends for their assistance, which helped me finish this project. Their help made my ideas more refined and the research better.

Biggest thanks for all your support and encouragement that supported this research until this point.

Bryan Quinn Darlen,
17 December 2025

---

## Abstract

The project will develop a web-based short-term air quality forecasting system for Malaysia using air quality measurements, weather data, and satellite fire hotspots as supporting evidence. A major problem is that air quality information is often reactive, while haze-driven pollution can change rapidly and disproportionately affect vulnerable populations. Furthermore, the drivers of the pollution are hard to interpret when air quality measurements, weather conditions, and hotspot indicators are not integrated together. In response, the research uses a multi-source data pipeline to periodically retrieve Air Pollutant Index data from APIMS, meteorological data from METMalaysia, and active fire hotspots data from NASA FIRMS. The data will then undergo cleaning, time alignment, and integration into an hourly dataset that can be used for modelling.

The system will train and test machine learning models using a CRISP-DM workflow to produce 1–24-hour predictions, issue actionable alerts when thresholds are met, and provide user-friendly explanations that correlate predicted pollution spikes to weather patterns and hotspot activity. The result is represented as a dashboard that can be accessed through a FastAPI server to improve usability during unstable internet connections. It displays the most recent available data and the last update time, even when the connection is weak. The importance of the project lies in supporting earlier risk-avoidance decisions and public trust through air quality information. The project aligns with SDG 3 by minimizing the risk of exposure through timely warnings, SDG 11 by improving environmental awareness and preparedness in the city, and SDG 13 by responding to climate-related haze and fire incidents.

**Keywords:** Air quality nowcasting, API forecasting, Machine learning, APIMS, METMalaysia, NASA FIRMS

---

## Table of Contents

- [Acknowledgement](#acknowledgement)
- [Abstract](#abstract)
- [Chapter 1: Introduction](#chapter-1-introduction)
  - [1.1 Introduction](#11-introduction)
  - [1.2 Problem Statement](#12-problem-statement)
  - [1.3 Project Aim](#13-project-aim)
  - [1.4 Objectives](#14-objectives)
  - [1.5 Scope](#15-scope)
  - [1.6 Potential Benefits](#16-potential-benefits)
  - [1.7 IR Overview](#17-ir-overview)
  - [1.8 Project Plan](#18-project-plan)
- [Chapter 2: Literature Review](#chapter-2-literature-review)
  - [2.1 Introduction](#21-introduction)
  - [2.2 Domain Research](#22-domain-research)
  - [2.3 Similar Systems and Works](#23-similar-systems-and-works)
  - [2.4 Technical Research](#24-technical-research)
  - [2.5 Summary](#25-summary)
- [Chapter 3: Methodology](#chapter-3-methodology)
  - [3.1 Introduction](#31-introduction)
  - [3.2 Methodology](#32-methodology)
  - [3.3 Data Collection](#33-data-collection)
  - [3.4 Initial Data Pre-processing and Data Understanding](#34-initial-data-pre-processing-and-data-understanding)
  - [3.5 Data Merge](#35-data-merge)
  - [3.6 Summary](#36-summary)
- [Chapter 4: Conclusion](#chapter-4-conclusion)
  - [4.1 Critical Evaluation](#41-critical-evaluation)
  - [4.2 Limitation](#42-limitation)
  - [4.3 Recommendation](#43-recommendation)
- [References](#references)
- [Appendices](#appendices)

---

## List of Figures

| Figure | Description |
|--------|-------------|
| Figure 1 | Major health risk in Air Pollution. (American Heart Association, n.d.) |
| Figure 2 | Higher PM10 levels are linked to higher respiratory admission risk over time. (Hanin et al., 2023) |
| Figure 3 | Reactive vs. predictive air quality reporting. |
| Figure 4 | Forecasting next day air pollutant index in Malaysia. |
| Figure 5 | Spatial distribution of fire specific PM2.5 in the Asia Pacific region. (Lu et al., 2025) |
| Figure 6 | Air quality around ASEAN. (Livingasean, 2023) |
| Figure 7 | Air quality index categories are used to communicate risk levels to the public. (Rizwan, 2025) |
| Figure 8 | Deaths from outdoor particulate matter air pollution by age. (Ritchie, H., & Roser, M, 2024) |
| Figure 9 | SDG 3. (Joint SDG Fund, 2022) |
| Figure 10 | The flow of communication of AQI in Malaysia. |
| Figure 11 | API Band. (Lyons et al., 2016) |
| Figure 12 | Meteorological impact on short-term air pollution changes. |
| Figure 13 | Weather and pollution interaction impact risk ratio. |
| Figure 14 | The FIRMS hotspot map. (Koala_on_a_Treadmill, n.d.) |
| Figure 15 | Atmospheric organic carbon distribution. (Sumaryati et al., 2022) |
| Figure 16 | Illustration forecast for the next 1–24 hours. (Minh et al., 2021) |
| Figure 17 | Windows 11 logo. (Microsoft, n.d.) |
| Figure 18 | CRISP-DM phase. (Chumbar, 2023) |
| Figure 19 | Import APIMS libraries. |
| Figure 20 | APIMS endpoint. |
| Figure 21 | FastAPI application. |
| Figure 22 | Fetch APIMS. |
| Figure 23 | Import METMalaysia libraries. |
| Figure 24 | METMalaysia endpoint. |
| Figure 25 | FastAPI app for METMalaysia and 2 new variables. |
| Figure 26 | Fetch METMalaysia data. |
| Figure 27 | Import NASAFirms libraries. |
| Figure 28 | NASAFirms endpoint. |
| Figure 29 | NASAFirms FastAPI app and 2 variables. |
| Figure 30 | Fetch NASAFirms data. |
| Figure 31 | Preprocess APIMS JSON. |
| Figure 32 | Keeps selected APIMS columns. |
| Figure 33 | APIMS time conversion. |
| Figure 34 | Standardize APIMS columns. |
| Figure 35 | Handle APIMS duplicate rows. |
| Figure 36 | Ensure numeric types on selected APIMS columns. |
| Figure 37 | APIMS information. |
| Figure 38 | Preprocess METMalaysia JSON. |
| Figure 39 | Turn JSON to DataFrame. |
| Figure 40 | Rename METMalaysia columns. |
| Figure 41 | Parse METMalaysia timestamp. |
| Figure 42 | Remove METMalaysia degree symbol rows. |
| Figure 43 | Count METMalaysia rainy forecast slots. |
| Figure 44 | Convert METMalaysia rainfall dict to string. |
| Figure 45 | Remove METMalaysia duplicate rows. |
| Figure 46 | Reset METMalaysia DataFrame index. |
| Figure 47 | METMalaysia information. |
| Figure 48 | Preprocess NASAFirms. |
| Figure 49 | Standardize NASAFirms columns. |
| Figure 50 | Keep selected NASAFirms columns. |
| Figure 51 | Combine NASAFirms acquisition date and time. |
| Figure 52 | Remove original NASAFirms date and time columns. |
| Figure 53 | Convert selected columns into numeric format. |
| Figure 54 | Filter NASAFirms hotspot records. |
| Figure 55 | Rename NASAFirms columns. |
| Figure 56 | Remove NASAFirms duplicate rows. |
| Figure 57 | Reset NASAFirms index. |
| Figure 58 | NASAFirms information. |
| Figure 59 | APIMS total rows, columns and first 5 rows. |
| Figure 60 | Description of APIMS data. |
| Figure 61 | APIMS unique value count. |
| Figure 62 | APIMS attributes and observations. |
| Figure 63 | Histogram of API Distribution. |
| Figure 64 | Correlation Heatmap. |
| Figure 65 | METMalaysia total rows, columns, and the first five records. |
| Figure 66 | Description of METMalaysia data. |
| Figure 67 | METMalaysia unique value count. |
| Figure 68 | METMalaysia attributes and observations. |
| Figure 69 | Distribution of Temperature Histogram. |
| Figure 70 | Bar Chart of Avg Rain Forecast Slots per State. |
| Figure 71 | NASAFirms total rows, columns, and the first five rows. |
| Figure 72 | Description of NASAFirms data. |
| Figure 73 | NASAFirms unique value count. |
| Figure 74 | NASAFirms attributes and observations. |
| Figure 75 | Distribution of FRP Histogram. |
| Figure 76 | Bar Chart of Hotspot Count by Confidence Level. |
| Figure 77 | Hotspot Geographic Distribution Heatmap. |
| Figure 78 | Loads three preprocessing models. |
| Figure 79 | Select APIMS columns. |
| Figure 80 | Select METMalaysia columns. |
| Figure 81 | Select NASAFirms columns. |
| Figure 82 | Round to Hour. |
| Figure 83 | Aggregate NASAFirms hourly. |
| Figure 84 | Clean States. |
| Figure 85 | Merge all datasets. |
| Figure 86 | Rounds APIMS and METMalaysia time. |
| Figure 87 | Applies clean state for APIMS and METMalaysia. |
| Figure 88 | Creates empty FIRMS hourly placeholder. |
| Figure 89 | Left joins APIMS with METMalaysia. |
| Figure 90 | Left joins merged table with hourly NASAFirms. |
| Figure 91 | Fills missing NASAFirms columns. |
| Figure 92 | Drops selected columns. |
| Figure 93 | Sorts the table and resets index. |
| Figure 94 | Merged Data attributes and observations. |
| Figures 95–114 | PPF – Project Title Proposal (pages 1–20). |
| Figures 115–119 | Fast Track Ethics Form. |
| Figures 120–122 | Log Sheets. |
| Figure 123 | Gantt Chart. |

---

## List of Tables

| Table | Description |
|-------|-------------|
| Table 1 | Project Plan |
| Table 2 | Similar Systems and Works |
| Table 3 | Processor Specification |
| Table 4 | Softwares and Usages |
| Table 5 | Dataset Name, Source, and Format from three datasets |
| Table 6 | APIMS information and description |
| Table 7 | METMalaysia information and description |
| Table 8 | NASAFirms information and description |
| Table 9 | APIMS attributes and observations |
| Table 10 | METMalaysia attributes and observations |
| Table 11 | NASAFirms attributes and observations |
| Table 12 | Merged Data attributes, observations, and functions |
| Table 13 | Respondent Demographic Profile |

---

# Chapter 1: Introduction

## 1.1 Introduction

Air pollution is a serious issue since the level of pollutants can fluctuate rapidly and influence day-to-day life. In Malaysia, these changes can make outdoor activities more uncomfortable and can be dangerous to health, particularly for sensitive populations. This leads to the necessity to create improved awareness and up-to-date information regarding present and future air quality.

According to research on health, air pollution is not only associated with breathing issues but also with the cardiovascular system. Air pollution may pose health risks to the heart from polluted air particles, which justifies the importance of minimizing exposure by providing earlier notifications and prevention (Feldscher, K., 2025).

Malaysia has a system of measuring ambient air quality that is administered by the Department of Environment (DOE), which reports near real time using the Air Pollution Index Management System (APIMS). This platform also posts Air Pollutant Index data and other updates, which people can rely on to be aware of the present-day air quality of various locations (MyEQMS, n.d.).

Thus, the purpose of this project is to forecast air pollution in Malaysia based on real-time information that will allow determining short-term trends and not only observing them afterward. The project contributes to SDG 3 (Good Health and Well-Being) by allowing individuals to minimize exposure to risks, and contributes to sustainable cities and communities through environmental management.

---

## 1.2 Problem Statement

### 1. Air Pollution Remains a Serious Health Risk During Haze Events

*Figure 1: Major health risk in Air Pollution. (American Heart Association, n.d.)*

Serious health problems, particularly diseases that involve the lungs and the heart, are closely linked to air pollution. It is known as one of the major environmental health risks because prolonged exposure can affect breathing, place stress on the heart, and increase the risk of premature death (World Health Organization, 2024). In daily life, this implies that poor air quality is not only a main environmental issue but also a direct health impact to the people. Older adults, children, and individuals with asthma tend to have higher risk due to their quicker response to dirty air. Exposure to polluted air can cause coughing, shortness of breath, and asthma attacks, particularly when fine particle levels are high (World Health Organization, 2024).

*Figure 2: Higher PM10 levels are linked to higher respiratory admission risk over time. (Hanin et al., 2023)*

This issue is more evident in Malaysia during haze seasons. It has been found that when particulate pollution increases during haze seasons, the number of hospitalizations also rises over time. This indicates that air pollution affects individuals seriously enough to require medical intervention (Sofwan et al., 2021; Mohd Zulkifli et al., 2024).

Furthermore, this trend highlights a major public health concern. Most individuals tend to respond when the air is already unhealthy, although preventive actions should be taken earlier. Late or unclear warnings can cause the community to miss the appropriate time to minimize exposure, such as reducing outdoor activities and wearing masks. This problem is directly related to SDG 3, which aims to reduce illnesses and deaths due to pollution and improve health outcomes (United Nations, 2024).

### 2. Air Quality Reporting Is Largely Reactive, Limiting Short-Term Preparedness

*Figure 3: Reactive vs. predictive air quality reporting.*

Hourly forecasting models and other short-term prediction models are useful because they give people time to prepare before air quality deteriorates. Furthermore, hourly forecasting can deliver information that assists in making future decisions (Tran et al., 2023). People need this model because air pollution can change rapidly during haze periods. Late responses may imply that people have been exposed for several hours.

In addition, warning systems do not do much in terms of timely notifications. According to Park et al. (2023), air quality alerts can influence health-related outcomes in vulnerable areas. This implies that alerts are effective when delivered at the right time and with clear messages for people to act on. By combining short-term forecasts and alerts, the system can assist early and practical protection measures while minimizing unnecessary exposure. This relates to SDG 3 because early warning and early action can reduce the health impacts caused by pollution, particularly in vulnerable areas (United Nations, 2024).

Furthermore, studies on API from Malaysia indicate a practical gap that supports the view that preparedness is hindered by reactive reporting. The article indicates that Malaysia does not have a system to predict next-day API readings, and it suggests a forecasting method that uses hourly API readings to predict API the following day. The paper highlights that next-day forecasting can assist vulnerable populations in planning their daily activities in advance and help governments provide earlier health warnings by preparing for likely conditions (Awang et al., 2000).

### 3. Pollution Drivers Are Hard to Identify Due to Fragmented Information Sources

*Figure 5: Spatial distribution of fire specific PM2.5 in the Asia Pacific region. (Lu et al., 2025)*

Fine particulate pollution in the Asia Pacific region can be a significant contributor of fires. Individuals are not always affected equally because it depends on the season and location. There are times when burning is more active and the weather is drier — smoke forms more easily and can remain in the air for longer periods (Lu et al., 2025). In Southeast Asia, haze events tend to be more intense when smoke from burning regions is carried over long distances. This implies that pollution levels in a city may suddenly increase even when there are no obvious local sources. Due to this fact, relying on local air quality readings alone can be misleading. The readings may demonstrate that pollution is high, but do not explicitly indicate the source of the pollution or why it increased at that time (Lu et al., 2025).

*Figure 6: Air quality around ASEAN. (Livingasean, 2023)*

Polluted air masses are not a new problem in Southeast Asia, and it makes it difficult to explain pollution sources using air quality measurements alone (Nguyen et al., 2022). Satellite hotspot products offer near real-time indications of active fires and are extensively utilized through open platforms because the hotspots can serve as proof of potential smoke sources (Hope et al., 2024; Coskuner et al., 2022). However, hotspot maps are mostly not combined with local air quality data and weather conditions.

This separation complicates the public's ability to connect the information. High pollution may be observed in individuals' neighbourhoods, but they may not know whether it is associated with nearby fires, fires in upwind areas, or haze movement across a region. If the information is scattered, public awareness becomes weaker and protective measures may be postponed. This problem statement is associated with SDG 3, which aims to reduce illness and deaths caused by pollution by improving prevention and protecting public health (United Nations, 2024).

### 4. Unclear or Inconsistent Air Quality Messaging Can Erode Public Trust

*Figure 7: Air quality index categories are used to communicate risk levels to the public. (Rizwan, 2025)*

Clarity and accuracy of air quality information are important because they determine the way individuals respond. When the air is reported as good, individuals will think it is safe and proceed with normal outdoor activities even if the risk is still high. This reduces their sense of danger and leads to behaviours that increase exposure, such as outdoor exercise. It has been found that false information about good air quality may reduce public risk perception, underscoring that accuracy and clear messages are essential. The public is directly influenced by decisions related to public safety (Zhang et al., 2025).

From the public perspective, trust comes from clear and consistent reports. Once the numbers or messages are confusing or do not correspond to what people are experiencing, users can disregard warnings or stop using the system. Simultaneously, many air quality prediction systems are difficult to interpret.

According to reviews, a model provides the prediction of air quality, but users and decision makers might not trust it if the system is unable to provide sufficient reasons (Houdou et al., 2024). This is a significant issue because a forecast is not only a technical output, but also a message that affects behaviour. Health communication messages also clarify that short-term health risks are communicated through air quality indexes (World Health Organization, 2026). A system that provides predictions together with explanations can assist users to understand the current air quality conditions. It contributes to SDG 3 because it assists the public to make better decisions that minimize the health effects of pollution (United Nations, 2024).

---

## 1.3 Project Aim

The project aim is to design a real-time air quality app in Malaysia, which uses APIMS data, METMalaysia weather, and NASA FIRMS fire hotspot alerts. The system will be deployed as a web dashboard that provides forecasts, alerts, and clear explanations of the causes of pollution, even with weak internet connectivity.

---

## 1.4 Objectives

1. To implement a data pipeline that fetches, cleans, and merges APIMS, METMalaysia, and NASA FIRMS data regularly.
2. To build a short-term air pollution module which generates alerts once the levels hit beyond the safe range and display the results in output.
3. To design a user interface system that explains the causes of pollution using weather forecasts and hotspot evidence, while supporting offline mode that displays the last cached data and last updated timestamp.

---

## 1.5 Scope

### 1.5.1 Deliverables

This project creates a backend service that gathers information about air quality from APIMS, weather information from METMalaysia, and active fire hotspots information from NASA FIRMS. The backend will filter the data received and standardize the formats accordingly.

The project will also develop a short-term forecasting/nowcasting component which will generate predictions of the coming one to twenty-four hours. The system will impose alert rules such that users will be notified in case the pollution reaches actionable levels, such as conditions linked with haze-response guidance.

Lastly, the project will develop a web user interface that shows the present conditions, trends, forecast, and simplified explanation of probable reasons by associating air-quality variation with weather patterns and hotspot presence. The interface will have an offline mode that shows the last saved data.

### 1.5.2 Constraints

- The system depends on external data availability from data sources, and real-time behaviour is limited by how often the sources update new data.
- Once the internet is not strong enough or unavailable, the system will not be able to download new data. It uses information that has been saved previously until the connection is restored.
- Continuous data collection and processing from multiple sources can increase CPU workload, which affects performance during tests.

### 1.5.3 Scheduled & Excluded Tasks

**Scheduled Tasks**

- Combine various data sources in one automated pipeline which cleans and combines the data.
- Produce short-term predictions of up to 24 hours and issue alerts when pollution attains action levels.
- Include an explanation feature which connects the variations in air quality with weather conditions and hotspot activity.
- Provide an offline mode by showing the last cached data and last updated date.

**Excluded Tasks**

- The project will not construct new physical sensors, as it will use the existing sources of online data.
- It will not venture into long-term projections outside the short-term frame as outlined in the blueprint.
- It will not deliver a full mobile application and will be focused on the web user interface.

### 1.5.4 Targeted Users

- Malaysian students, parents, and schools that need air-quality information to make decisions for outdoor activities.
- Young women and teenagers, especially those with asthma and frequent breathing symptoms.
- Middle-aged and older adults that have asthma symptoms and other chronic respiratory ailments which require early alerts during periods of pollution peaks.

---

## 1.6 Potential Benefits

### 1.6.1 Tangible Benefits

The project provides an operational web-based platform that retrieves official air quality data on the Department of Environment Malaysia (APIMS) platform and integrates with METMalaysia weather data and NASA FIRMS fire hotspots data. It shows real-time monitoring graphs, short-term forecasts, and alert outputs to support decision making. The system also provides an offline mode display that retains the latest cached data and last updated time when internet connectivity is poor.

### 1.6.2 Intangible Benefits

The project enhances public knowledge of air quality data by reducing confusion about air quality numbers. It highlights the gaps between the misunderstanding of index values, measurements of the pollutants, and uncertainty of weather conditions that can distort air quality readings. This improves decision-making during haze periods.

---

## 1.7 IR Overview

**Chapter 1: Introduction**
This chapter provides background information to readers with limited knowledge of the project domain. It provides the context of the problem, the single-sentence project purpose, outlines quantifiable goals, defines the scope including tasks, constraints, inclusions, and exclusions, identifies the intended users, and describes the deployment strategy. Lastly, it concludes with the possible benefits and the plan of the semester project.

**Chapter 2: Literature Review**
This chapter gives the findings of the literature review. It begins with general domain research and proceeds with technologies and methods. This is followed by a comparison of similar systems or works and their strengths and weaknesses. It ends with technical research that supports the hardware and software requirements, which are selected to be used in the proposed system.

**Chapter 3: Methodology**
This describes how the system will be developed. It explains the selected development methodology and its rationale, outlines activities and processes undertaken in each stage, and gives the data-gathering design supporting requirements and system capabilities. It ends with the results of analysis and a final list of user requirements.

**Chapter 4: Conclusion**
The last chapter serves as a concluding chapter of the investigation report. It talks about the accomplishments of the first half of the project, justifies the sufficiency of the investigation and research to support the direction of the project, and distinguishes the gaps in research or design that need to be investigated and enhanced.

---

## 1.8 Project Plan

*Table 1: Project Plan*

| Task Name | Duration | Start | Finish |
|-----------|----------|-------|--------|
| Project Summary | 63 days | Tue 16/12/25 | Thu 12/03/26 |
| PROJECT PROPOSAL FORM | 16 days | Tue 16/12/25 | Tue 06/01/26 |
| INVESTIGATION REPORT | 23 days | Tue 10/02/26 | Thu 12/03/26 |
| Acknowledgement | 1 day | Tue 10/02/26 | Tue 10/02/26 |
| Abstract | 1 day | Tue 10/02/26 | Tue 10/02/26 |
| **Chapter 1: Introduction** | 4 days | Wed 11/02/26 | Sat 14/02/26 |
| 1.1 Introduction | 1 day | Wed 11/02/26 | Wed 11/02/26 |
| 1.2 Problem Background | 1 day | Wed 11/02/26 | Wed 11/02/26 |
| 1.3 Project Aim | 1 day | Thu 12/02/26 | Thu 12/02/26 |
| 1.4 Objectives | 2 days | Thu 12/02/26 | Fri 13/02/26 |
| 1.5 Scope | 2 days | Fri 13/02/26 | Sat 14/02/26 |
| 1.6 Potential Benefit | 1 day | Sun 15/02/26 | Tue 17/02/26 |
| 1.6.1 Tangible Benefit | 1 day | Sun 15/02/26 | Sun 15/02/26 |
| 1.6.2 Intangible Benefit | 1 day | Mon 16/02/26 | Mon 16/02/26 |
| 1.6.3 Target User | 1 day | Tue 17/02/26 | Tue 17/02/26 |
| 1.7 Overview of IR | 2 days | Tue 17/02/26 | Wed 18/02/26 |
| 1.8 Project Plan | 1 day | Thu 19/02/26 | Thu 19/02/26 |
| **Chapter 2: Literature Review** | 8 days | Fri 20/02/26 | Tue 31/03/26 |
| 2.1 Introduction | 1 day | Fri 20/02/26 | Fri 20/02/26 |
| 2.2 Domain Research | 5 days | Sat 21/02/26 | Fri 27/02/26 |
| 2.3 Similar Systems/Works | 2 days | Sat 28/02/26 | Tue 03/03/26 |
| 2.4 Technical Research | 1 day | Wed 04/03/26 | Wed 04/03/26 |
| 2.5 Summary | 1 day | Wed 04/03/26 | Wed 04/03/26 |
| **Chapter 3: Methodology** | 5 days | Thu 05/03/26 | Wed 11/03/26 |
| 3.1 Introduction | 1 day | Thu 05/03/26 | Thu 05/03/26 |
| 3.2 Methodology | 1 day | Fri 06/03/26 | Fri 06/03/26 |
| 3.3 Data Collection | 2 days | Fri 06/03/26 | Sat 07/03/26 |
| 3.4 Initial Data Understanding and Preprocessing | 3 days | Sat 07/03/26 | Wed 11/03/26 |
| 3.4.1 Data Understanding | 2 days | Sat 07/03/26 | Tue 10/03/26 |
| 3.4.2 Data Preprocessing | 1 day | Tue 10/03/26 | Tue 10/03/26 |
| 3.4.3 Data Understanding | 1 day | Wed 11/03/26 | Wed 11/03/26 |
| 3.5 Summary | 1 day | Wed 11/03/26 | Wed 11/03/26 |
| **Chapter 4: Conclusion** | 1 day | Thu 11/03/26 | Thu 11/03/26 |
| References | 1 day | Thu 11/03/26 | Thu 11/03/26 |
| Appendices | 1 day | Thu 11/03/26 | Thu 11/03/26 |

---

# Chapter 2: Literature Review

## 2.1 Introduction

The following chapter reviews project domain and knowledge that is essential in developing a Malaysia real-time air quality system. The discussion starts with the health and sustainable development relevancy, followed by the explanation of the connection between air quality indices, weather conditions, fire hotspots, and short-term changes in pollution. It also scans comparable systems, current research, and technical research that guide implementation decisions for the system, like data retrieval, data storage, forecasting, and delivery of the user interface.

---

## 2.2 Domain Research

### 2.2.1 Air pollution, public health, and SDG alignment

*Figure 8: Deaths from outdoor particulate matter air pollution by age. (Ritchie, H., & Roser, M, 2024)*

Air pollution is one of the main environmental risks to human health because it has numerous bad impacts on the body. The reviewed evidence shows that chronic and repeated exposure to polluted air is associated with increased risk of cardiometabolic disease, respiratory disease, and even neurological disease, with a general increase in mortality (Shazia Iram et al., 2025). The issue is important because air pollution affects a large proportion of the population. Most of the population is exposed daily, particularly those who live in urban areas or close to roads, industrial areas, or regions where burning is a common occurrence. In some cases, the lack of apparent symptoms does not mean that air pollution is harmless — it still causes gradual biological changes that accumulate over time and increase the risk of disease (Sigsgaard & Hoffmann, 2024).

Air pollution is characterized by two categories of pollutants: gases and particles. Gas pollutants such as nitrogen dioxide can irritate the airways and cause inflammation. The size of particulate matter is defined by its diameter — smaller particles may penetrate deeper into the lungs. PM2.5 is a particle less than 2.5 micrometres and PM10 is less than 10 micrometres. The review describes that exposure to both particles and gases is significant because individuals are typically exposed to multiple pollutants. These pollutants are from large-scale human activities that include energy generation, industrial processes, road traffic, heating, and agriculture. Since these sources are widespread, exposure may occur in many locations (Sigsgaard and Hoffmann, 2024).

One of the highlights in this review is that air pollution does not affect the lungs only. Exposure to air pollution can affect most organ systems and cause a wide range of physiological responses. This is because pollutants may cause inflammation and oxidative stress, which subsequently impacts blood vessels, metabolism, and other biological functions. These changes may result in organ dysfunction and clinical disease. To summarize the health effects (Sigsgaard & Hoffmann, 2024):

- **Respiratory system:** Airway irritation, aggravation of asthma symptoms, increased risk of respiratory disease.
- **Cardiometabolic:** Heart and blood vessel stress, predisposition to cardiovascular diseases, associations with metabolic issues.
- **Neurological effects:** Increasing signs of effects on brain health and risk of neurological disease.
- **Consequences:** More disease burden and greater risk of premature mortality.

The review emphasizes that a comprehensive burden of disease assessment is required because the effects of air pollution are severe (Shazia Iram et al., 2025). This assessment must capture the full range of exposure-outcome associations within a population to understand the role of pollution in causing disease and mortality. It is also significant for prevention, since policy makers and public health agencies require robust evidence to determine which interventions to prioritize. When an assessment is based only on a limited number of outcomes, the actual effect may be underestimated, leading to weaker prevention measures. Conversely, a better comprehensive evaluation that takes multiple paths and outcomes into account can support more effective population-based prevention measures, including reducing emissions from major sources and strengthening public warning systems during bad pollution events (Sigsgaard and Hoffmann, 2024).

*Figure 9: SDG 3. (Joint SDG Fund, 2022)*

The next research points out that the correlation between air pollution and SDGs is not given sufficient attention. According to their evaluation, air pollution has a negative impact on 71 of 169 SDG targets, and only 6 targets might be positively impacted. The paper also mentioned that air pollution is automatically linked to health and sustainable cities goals, which can have an impact on other areas such as agriculture, food security, and ecosystem (Zhou et al., 2024).

Furthermore, the case study from China examines two major nitrogen-related air pollutants: ammonia and nitrogen oxides. The research shows that these pollutants resulted in significant economic losses in 2020. It also simulates how reducing these losses by 2030 can lower economic damage. The research indicates that the mitigation of ammonia and nitrogen oxide may support SDG development and generate overall returns that exceed the implementation cost. Ammonia was found to be the more cost-efficient priority. Overall, the paper claims that strong scientific evidence should be used to inform integrated policies to ensure that enhancing air quality can also contribute to sustainable development objectives (Zhou et al., 2024).

### 2.2.2 Air quality reporting, communication and actionable thresholds in Malaysia

*Figure 10: The flow of communication of AQI in Malaysia.*

Air quality communication is most effective when it transforms technical measurements into simple categories and actionable guidance. In Malaysia, air pollution is reported through API (Air Pollutant Index) and a network of continuous air quality monitoring stations that offers hourly data for quality control measures. Studies also indicate that seasonal weather conditions and haze have a strong influence on pollution trends. This implies that air quality messages should be based on clear index bands and practical thresholds (Rahman et al., 2022; Sokhi et al., 2022).

In Malaysia, PM2.5 is considered one of the pollutants with the biggest concern in air quality monitoring. Research uses PM2.5 measurements from 65 stations and demonstrates that it is continuously monitored with specific equipment. Moreover, it supports the use of PM2.5 as a primary indicator for short-term tracking. The paper also defines PM2.5 as one of the most significant pollutants for health risk assessment.

Malaysia monitors air quality through a network of stations, where the data are sent to the Environmental Data Centre and undergo quality assurance and quality control processes. This reinforces the importance of using validated data in reporting. It aligns with broader studies that emphasize measurement quality and stable monitoring systems as the key to protecting public health.

The Air Pollutant Index in Malaysia is determined using six criteria pollutants, with a sub-index calculated for each pollutant every hour. The hourly Air Pollutant Index is based on the pollutant with the highest sub-index. The index has clear bands ranging from good to hazardous levels. This design assists the public in quickly understanding pollution levels and making decisions based on available thresholds. It also emphasizes the importance of clear communication tools and forecasting systems in minimizing exposure during acute pollution seasons.

The study applies agglomerative hierarchical clustering to classify PM2.5 monitoring stations into high, medium, and low pollution regions. It records different average PM2.5 levels across clusters, showing these clusters are not evenly distributed throughout Malaysia. This supports the need for location-based reporting and local thresholds. More broadly, other studies have shown that cities are influenced by local pollution gradients and long-distance transport, making local context important in public communication.

The research indicates that the highest PM2.5 levels were recorded during the 2019 Southeast Asian haze, when Air Pollutant Index reached hazardous levels. It also reports that unhealthy and very unhealthy API levels were more prevalent in 2019 than in 2018. This supports the need for explicit warnings and prior intervention during haze. Sokhi et al. supports this trend by stating that the ability to predict peak concentrations can be used to prevent and mitigate health effects through advance planning.

Moreover, the research indicates that PM2.5 and PM10 have strong correlations in all areas and also show significant correlations with carbon monoxide, while meteorological variables show weaker but still significant relationships. This supports the integration of index reporting with simple supporting indicators, such as weather patterns and haze signals, to help the public understand why pollution levels may vary. A broader trend is the integration of remote sensing, ground monitoring, improved forecasting, and user-focused information services that further supports the importance of integrated explanations in real-world applications (Rahman et al., 2022; Sokhi et al., 2022).

*Figure 11: API Band. (Lyons et al., 2016)*

The API bands shown above are commonly used in the public community. These bands inform the public whether air quality is safe or unsafe. According to a report from RTM, Malaysia relies on clear Air Pollutant Index thresholds as operational guidelines for schools during haze periods. According to the Ministry of Education, schools are required to check the IPU readings and take immediate actions when the air quality is not safe. When the IPU exceeds 100, outdoor activities should be stopped immediately for safety purposes. Once the IPU is more than 200, schools are expected to close and transition to home-based learning as standard operating procedure.

Another important point in the report is that state education departments, district education offices, and schools are required to take preventive measures when the IPU reaches unhealthy level, demonstrating that index functions are not only represented as information but also as a trigger for protective action. The report provides an example during haze conditions, stating that at 5:00 p.m., several places including Cheras, Nilai, and Seremban recorded unhealthy IPU levels, which affected schools in those areas to halt outdoor activities and adopt safety precautions. Furthermore, IPU categories and thresholds are useful communication tools because they translate air quality indicators into clear responses that help protect students, teachers, and school communities during pollution periods (RTM, 2023). According to the Department of Environment, APIMS is also a national platform that provides real-time environmental information to the public (Department of Environment Malaysia, 2025).

### 2.2.3 Meteorological influences on short-term changes in air pollution

*Figure 12: Meteorological impact on short-term air pollution changes.*

Meteorology influences short-term changes in air pollution. Weather conditions affect the accumulation, dispersion, and persistence of pollutants in the atmosphere. Temperature and humidity may impact day-to-day pollution trends and influence health risks to individuals. Some studies indicate that weather conditions and air pollution exposure are associated with disease outcomes.

Other researchers have indicated that short-term pollution levels can be predicted using weather data. These results suggest that short-term pollution should not rely only on air readings. Taken together, these findings support the use of meteorological signals to improve forecasting and make pollution patterns more understandable (Rus & Mornos, 2022; Ulpiani et al., 2022; Lu et al., 2021).

The review on acute coronary syndromes states that seasonal changes in meteorological factors lead to an increased risk of acute coronary events. It further indicates that rises and falls in temperature were reported as risk factors for acute coronary syndrome admissions. This is important for air quality systems because it demonstrates that even without long-term exposure, weather changes may cause short-term periods of elevated risk. The same review also indicates that cardiovascular mortality increases with exposure to high levels of air pollutants. It presents the risk as a combined problem in which both meteorological variation and air pollution contribute to health outcomes (Rus & Mornos, 2022). This supports the need for short-term warning systems that track both weather patterns and pollution levels.

Evidence from an environmental health study in Northeast China also demonstrates that meteorology is associated with pollution-related health outcomes. The research indicates that atmospheric pollutants such as PM2.5 and PM10 are positively correlated with the occurrence of allergic conjunctivitis. It also records a positive relationship with meteorological conditions including air temperature and wind speed. By contrast, relative humidity shows a negative relationship with disease incidence. This gives a conclusion that hot weather and lower humidity may coincide with increased health risk during pollution events. Thresholds of both pollutants and meteorological factors are also estimated in the study. It records PM10 and PM2.5 thresholds of 70 μg/m³ and 45 μg/m³ respectively. Threshold values for gases include SO₂ at 23 μg/m³, NO₂ at 27 μg/m³, O₃ at 88 μg/m³, and CO at 0.82 mg/m³. For meteorology, the threshold values of air temperature and relative humidity are reported at 5.5°C and 60% respectively. These thresholds demonstrate how meteorological and pollution variables can be translated into practical warning points (Lu et al., 2021). Although the study focuses on allergic conjunctivitis, the findings still support the broader argument that meteorology helps explain short-term risk patterns and pollution exposure.

Furthermore, some learnings demonstrate that the relationship between weather and short-term health risk may vary according to the long-term pollution background. A study of 21 cities in Southwest China examined how weather and air pollution can cause related hand, foot, and mouth disease in children. It applied a distributed lag non-linear model to assess short-term effects and combines this with meta-regression using long-term city-level pollution indicators.

*Figure 13: Weather and pollution interaction impact risk ratio.*

It states that long-term SO₂ and CO levels had a significant effect on the short-term association between climatic variables and disease prevalence. It documents that increased CO and SO₂ minimized risks in low temperatures. Moreover, it records that the association between relative humidity and disease occurrence was weaker at high SO₂ concentration, particularly when relative humidity was lower than the median. An example provided shows that minimum relative humidity at 32% and median relative humidity at 77% is reported to have a risk ratio of 0.77 in the 90th percentile of SO₂ and 0.41 in the 10th percentile of SO₂. This indicates that the effects of weather can vary depending on the pollution background. It supports the idea that short-term systems should look at current conditions and long-term pollution trends when interpreting meteorological signals (Luo et al., 2022).

In addition to health association studies, forecasting research also favours meteorology as a viable cause of short-term pollution variation. One study from Sydney tested long short-term memory forecasting models using historical hourly data from nine sites. Researchers forecasted five types of urban pollution and tested these models during normal times and unique events, such as bushfires or pandemic lockdowns.

The research states that adding many predictors beyond temperature and humidity does not improve the forecasting algorithm because the model can learn long-term dependencies. Furthermore, ozone was found to be more sensitive to weather conditions. PM10 was found to be less predictable than other pollutants in the study. It is also stated that prediction accuracy under standard conditions and during bushfire events was similar, but predictability was lower during the pandemic period since anthropogenic activity patterns changed.

Overall, it concludes that accurate prediction of PM10 requires the inclusion of local emission sources and human activity factors. Weather information alone is not sufficient for some pollutants when patterns of human activity change (Ulpiani et al., 2022).

### 2.2.4 Fire hotspots as evidence of haze and smoke influence

*Figure 14: The FIRMS hotspot map. (Koala_on_a_Treadmill, n.d.)*

The Fire Information for Resource Management System (FIRMS), developed by NASA, is a widely used near real-time source of fire hotspot evidence because it offers MODIS and VIIRS fire products to users in numerous countries. The system was developed to assist managers who require real-time satellite-based fire information for required areas. Since 2006, FIRMS has been offering hotspot data in several formats, including a web map interface, email alerts, web mapping services, and files such as shapefiles and JSON. FIRMS was subsequently incorporated into NASA's Land, which provides satellite measurements within a few hours of overpass to support early responses (Davies et al., 2019).

Hotspot evidence is also practical because fire activity can be associated with increased particulate concentrations. Studies from Northern Thailand examined meteorological variables and fire hotspots together to understand the impact on particulate matter.

The research indicates that humidity, wind speed, temperature, and rainfall were negatively correlated to PM10 and PM2.5, while air pressure and fire hotspot counts were positively correlated with particulate matter. It also stated that the influence of these variables and fire hotspots on particulate matter levels lasted several days, demonstrating that smoke-related pollution and weather effects may not disappear within a day. This suggests that the number of hotspots may serve as evidence of possible smoke contributions (Sritong-aon et al., 2021).

*Figure 15: Atmospheric organic carbon distribution. (Sumaryati et al., 2022)*

The effects of haze and smoke influence become clearer when hotspot data are examined together with smoke movements. Research on major fire years in Indonesia describes that forest and land fires that peaked in 2015 and 2019 generated high levels of smoke. Hotspots detected by Aqua, Terra, and Suomi NPP satellites were used to describe fire activity. Meanwhile, aerosol optical thickness from VIIRS was used to represent aerosol loading. The study documents that fire events were associated with increased aerosol optical thickness and reduced visibility. Moreover, it demonstrates that hotspots may serve as a pointer for identifying haze events, while wind-driven smoke transport and aerosol conditions determined the haze effects (Sumaryati et al., 2022).

In general, these studies support the view that hotspots can be used as evidence of fire sources and smoke input. FIRMS offers accessible near real-time hotspot information that can be monitored and downloaded for system usage (Davies et al., 2019). Statistical and environmental research also demonstrates that the number of hotspots may coincide with increased particulate pollution, and their effects may last several days. Furthermore, weather conditions may either weaken or strengthen pollutant accumulation (Sritong-aon et al., 2021). Hotspot patterns, wind-driven smoke transport, and aerosol optical thickness were used to explain how smoke spreads across borders and reduces visibility (Sumaryati et al., 2022).

### 2.2.5 Short-term forecasting, explainability, and trust in predictive systems

*Figure 16: Illustration forecast for the next 1–24 hours. (Minh et al., 2021)*

Short-term forecasting is practical because it provides time to plan before air quality deteriorates. In Malaysia, one research study designed a hybrid forecasting model that integrates artificial neural network with triple exponential smoothing to forecast PM2.5 with previous measurements. The model was constructed based on historical PM2.5 data from 2018 to 2019 and tested on 2020 PM2.5 data ranging from low to high pollution region clusters. Moreover, the research indicates that the hybrid model recorded low error values with RMSE ranging from 4.25 to 8.56 μg/m³ and MAE spanning from 2.51 to 4.95 μg/m³. It also reports that forecast accuracy was adequate in high and medium pollution regions when compared to 2020 data, whereas the low pollution region showed lower performance with higher error. This confirms that short-term air quality prediction using historical indicators is viable for air quality management, even though accuracy can depend on regional conditions (Rahman et al., 2023).

Forecasting is not only about generating numerical outputs but also about making the system trustworthy and easy to use. A weather study in Kolkata applied supervised machine learning to forecast minimum and maximum temperatures for the next three days using a time series dataset of weather features from 1973 to 2024. It experimented with various models and reported that the gradient boosting regressor performed best. The study indicates strong one-day-ahead prediction performance using data from the past ten days, with RMSE up to 1.426 and MAE ranging around 1.0567. Furthermore, the study describes that explainable tools like LIME and SHAP were used to show the influence of variables such as wind speed and temperature, assisting users to understand model transparency and forecasting settings (Sarkar et al., 2025).

When the prediction output is applied in a decision support system, the issue of trust becomes more severe. Studies from air traffic management describe that highly automated AI systems can detect anomalies and predict risks, even though most of these algorithms are still difficult to interpret. Moreover, explainable artificial intelligence may be incorporated to enhance interpretability and transparency, which helps build trust among human operators. The paper introduces a methodology based on XGBoost to create a risk prediction model that analyses real-time situations and generates post-hoc explanations using SHAP and LIME. Most importantly, adoption can remain low if the system is not able to provide reasoning that human users can interpret (Xie et al., 2021).

A comparable concept can be seen in a building control study, where the issue is not about making predictions, but ensuring that users can interpret those predictions. The article focuses on automated supply air temperature prediction in an air handling unit using a regression model with a Huber loss optimization objective. It describes that a control curve is often sufficient, since building owners and technicians may not trust the algorithm without supporting evidence. The paper uses Shapley values to indicate the contribution of each feature and shows that the values provide a strong mathematical foundation for analysis (Eik et al., 2025).

---

## 2.3 Similar Systems and Works

*Table 2: Similar Systems and Works*

| Topic of Research | Author(s) | Description | Dataset Used | Methods of Analysis | Methods of Evaluation | Result/Outcomes | Limitations |
|---|---|---|---|---|---|---|---|
| Official Malaysia API public reporting | Department of Environment Malaysia | Public dashboard that reports official station readings and index categories | Official monitoring stations | Index computation and category classification | Operational monitoring validation | Trusted official status reporting for the public | Limited explanation of causes and limited short-term forecasting |
| Satellite hotspot monitoring platform | NASA FIRMS | Near real-time hotspot detection using satellite sensors and web services | MODIS and VIIRS active fire detections | Thermal anomaly detection and dissemination | Satellite product validation and operational checks | Fast hotspot visibility for decision support | Does not directly provide local pollution levels or personalised health guidance |
| Malaysia PM2.5 pattern and meteorology links | Rahman et al. | Study of PM2.5 behaviour across regions with weather relationships | Malaysia monitoring network data and meteorology | Statistical association analysis | Significance testing and comparative regional analysis | Shows weather variables relate to PM2.5 variation | Not a full real-time integrated system and not focused on user explanations |
| Malaysia-wide PM2.5 forecasting assessment | Tan et al. | Evaluates Malaysia-wide PM2.5 forecasts and discusses haze link to fires | Forecast model outputs and monitoring comparisons | Forecast comparison and performance checking | Error metrics and validation against observations | Shows forecasting is possible and measurable for Malaysia | May not provide simple user-facing explanations or offline use design |
| Malaysia PM2.5 estimation using satellite and ML | Zaman et al. | Produces high-resolution PM2.5 estimates using satellite and ML inputs | Multi-satellite data, ground pollutants, meteorology | Machine learning regression models | Cross validation and error metrics | Improves spatial coverage beyond sparse stations | Focus is estimation rather than real-time alerts and simple explanations |
| Aerosol and fire influence analysis in Malaysian Borneo | Sentian et al. | Studies aerosol variation with meteorology and fire records | MERRA-2 AOD and FIRMS fire records | Trajectory analysis and correlation analysis | Model comparison and source attribution reasoning | Strengthens evidence that fire activity influences aerosols | Research-oriented and not packaged as a public real-time system |

---

## 2.4 Technical Research

### 2.4.1 Hardware Justification

The development of this project uses a 13th Gen Intel Core i7-13650HX processor with 16 GB of RAM running on a 64-bit system. The current setup is suitable for long-term development since the system requires taking a lot of data frequently from multiple sources, cleaning the required values, and combining the datasets to prepare them for forecasting. Sixteen gigabytes of RAM is sufficient to work on large data tables while testing the web interface and running the backend service together. The Intel UHD Graphics are also sufficient since the project does not use heavy graphics rendering. Data preprocessing and web service implementation are the main workload in this development.

In addition, this hardware is efficient enough for multiple testing and debugging since it can handle many concurrent tasks during development, such as running the FastAPI server, scheduled jobs, writing logs, and displaying the dashboard in the browser. It supports local storage and caching in offline-friendly behaviour so the system can keep the latest merged dataset and update time on disk. Nevertheless, excessive running tests can increase CPU usage and heat because the system needs to keep downloading and processing data. To solve this, the data fetch schedule can be changed to a reasonable interval and unnecessary refreshes can be removed during test sessions.

*Table 3: Processor Specification*

| Component | Specification |
|-----------|--------------|
| Processor | 13th Gen Intel Core i7-13650HX @ 2.60 GHz |
| RAM | 16 GB |
| System | 64-bit operating system with x64-based processor |
| GPU | Intel UHD Graphics |

### 2.4.2 Software Justification

*Table 4: Softwares and Usages*

| Software | Usage |
|----------|-------|
| Python | Main language to fetch data, clean data, and merge data for forecasts. |
| FastAPI | Build backend services. |
| Uvicorn | Runs the FastAPI backend server so it can handle web requests. |
| APScheduler | Runs tasks automatically on a schedule. |
| Requests (or HTTPX) | Sends web requests to APIMS, METMalaysia, and NASA FIRMS to get JSON data. |
| Pandas | Cleans and combines datasets into a table for analysis. |
| NumPy | Helps with number operations within the data. |
| scikit-learn | Builds prediction models from the data. |
| SQLite | Saves the data in the database. |
| Visual Studio Code | Used to write code and debug the system. |
| Git | Tracks code changes and provides safe backup. |
| Web browser | Displays the dashboard and is used to test the user interface and offline display. |

The system requires several software tools to retrieve online data, process the data, run forecasting, and deliver the information to a web dashboard. Python is the primary language for this implementation since it is handy when dealing with data tables, cleaning records, and creating short-term prediction models. The backend service is built with FastAPI to create API endpoints that respond with recent combined data, forecasts, alerts, and explanations that are sent to the dashboard. Uvicorn is used to run the FastAPI application so it can serve FastAPI through the ASGI standard and handle requests when the dashboard is tested and refreshed. APScheduler is used to schedule automated updates of the merged dataset and forecast output by repeatedly fetching new APIMS, METMalaysia, and NASA FIRMS data.

SQLite is used as a storage option because it is lightweight and suitable for a prototype system that operates on a single machine. It aids local storage of the most recent merged data and forecast outcomes required for the offline-friendly requirement during weak internet connections. Pandas and NumPy are used to process data since they can process large volumes of time-based data through cleaning, reshaping, and merging. To evaluate and forecast, scikit-learn is used in this project because it offers the baseline models and conventional assessment measures to assess forecast performance. Coding and debugging are developed in Visual Studio Code, while version control is managed with Git to track changes safely and the web browser is used for testing the dashboard.

### 2.4.3 IDE (Interactive Development Environment)

Visual Studio Code is selected as the IDE, which uses Python as the backend and web datasets as the user interface. It assists Python code writing using auto-suggestions, debugging, and convenient choice of interpreter using the Python extension. It also allows usage of common web languages like HTML, CSS, and JavaScript within the same project folder. The terminal is used to run the FastAPI server and see logs when it is being tested.

### 2.4.4 Operating System

*Figure 17: Windows 11 logo. (Microsoft, n.d.)*

Windows 11 64-bit is chosen as the operating system in this project because it is stable for daily development and supports the entire software stack. It runs Python and FastAPI without issue and works with popular development tools like Visual Studio Code and Git. It is also easy to test since the web dashboard can be hosted locally and accessed in a browser on the same machine. The 64-bit system is significant as it can support more recent Python libraries and manage larger memory usage, which is beneficial in cleaning and combining several datasets and executing short-term forecasting programs.

### 2.4.5 Web Server

This project uses FastAPI with Uvicorn as the web server since the system requires a backend that can fetch JSON data from APIMS, METMalaysia, and NASA FIRMS. The backend cleans, combines, and transmits the data to the dashboard. It minimizes problems like browser cross-origin restrictions when accessing external APIs. The server can store the most recent merged data and the last updated time so that the interface may continue to provide previously cached results even when internet connectivity is poor.

---

## 2.5 Summary

In summary, this chapter has reviewed the main knowledge required to build a Malaysia real-time air quality system. The domain research addressed the problem of air pollution impacting people's health and discussed the importance of preventing air pollution. Then, it described how information about air quality should be presented in terms of index bands and actionable thresholds. It also examined the reasons behind short-term pollution variation — meteorological variables affecting dispersion and accumulation, haze and smoke effects aided by fire hotspot evidence, and short-term forecasting research which indicated the necessity of outputs that people could trust and comprehend.

Moreover, this chapter has compared similar systems and identified practical gaps which affect the usefulness of real-world applications, like disjointed sources of information and lack of explanation of the cause. Additionally, it showed the technical research required to make implementation decisions such as the chosen software and development environment, libraries, operating system, and web server options that will be utilized to implement data retrieval, storage, forecasting, and delivery of the user interface. Overall, the next chapter will outline the methodology and step-by-step procedure to construct the pipeline, prepare the data, and create the forecasting and dashboard elements.

---

# Chapter 3: Methodology

## 3.1 Introduction

This chapter describes the process of project implementation based on the CRISP-DM methodology. CRISP-DM offers a well-defined project flow that guides the project from problem definition to the deployment of a working system.

The chapter outlines the Business Understanding phase, which involves translation of the project goals into clear requirements. It describes the exploration of the data sources of APIMS, METMalaysia, and NASA FIRMS during the Data Understanding phase.

Furthermore, the chapter describes the process of preparing the data so that it becomes clean, consistent, and predictable. This involves the integration of air quality measurements, weather, and hotspot measurements to create a dataset that can be utilized by the prediction model.

Finally, the chapter discusses the process of model construction and testing, including the deployment of end results into the system. This involves the short-term prediction, alerting, plain cause descriptions, and offline-friendly presentation in terms of the last saved information and the last updated date.

---

## 3.2 Methodology

### 3.2.1 Introduction of CRISP-DM Methodology

CRISP-DM is a well-known data analytics approach that uses a step-by-step workflow. It is mostly applied to projects that aim to operate with real-world data, models, and useful outputs to users. CRISP-DM is applicable in this project because it begins with a clear problem and transforms it into a complete data product. Overall, this methodology covers the knowledge ranging from business understanding to deployment of a system.

### 3.2.2 Methodology and Justification

*Figure 18: CRISP-DM phase. (Chumbar, 2023)*

In this project, CRISP-DM methodology is chosen since the project is primarily data-driven. The system relies on various live data sources, and these sources are not of the same format. The main air quality signal is provided by APIMS. METMalaysia offers weather conditions which can alter the pollution degree. Hotspot signals are available in NASA FIRMS that help explain smoke events. CRISP-DM supports this work as it ensures the process begins with well-defined objectives followed by the phases of data processing. Generally, this can help minimize mistakes and ensure the output is based on reliable processing.

Furthermore, CRISP-DM is also suitable for this project since the desired outcome is an operational system that displays projections, warnings, and basic descriptions through a dashboard. CRISP-DM has a deployment stage to allow the model output to be linked to the backend and user interface. It also ensures fulfilling the offline-friendly mode since the deployment involves saving the latest merged data and updated time. The outcome is a defined workflow that enables both the technical build and end-user display.

### 3.2.3 CRISP-DM Phases

#### 3.2.3.1 Business Understanding

This phase establishes the problem and the purpose of the project. It sets the objectives, scope, success measures, limitations, and stakeholders. This stage ensures that the work is in line with the actual requirements before any data-related work commences. In this project, the identified requirement is to offer Malaysians a real-time, explainable air quality dashboard by connecting APIMS, METMalaysia, and NASA FIRMS in one pipeline. The target users include the general population, schools, and health-sensitive individuals, while one of the most important success measures is to provide correct 1–24-hour API predictions.

#### 3.2.3.2 Data Understanding

The main objective of the data understanding phase is to analyse existing data and its quality. It involves sample data gathering, reviewing formats, and identifying missing values, outliers, inconsistencies, and time gaps. The step helps determine what data are available and the problems that need to be addressed (Data Science PM, 2024). In this project, this step involves checking the APIMS hourly readings, METMalaysia weather snapshots, and NASA FIRMS hotspot CSV outputs to ensure that the key fields are available. All three sources are first examined through initial checks, such as counts of missing values, to determine any data quality problems before merging.

#### 3.2.3.3 Data Preparation

Data Preparation is essential in this phase because it converts raw data into useful insights for analysis. This phase covers the process of cleaning errors, handling missing values, standardising formats, merging data, and modelling features. Furthermore, this step generates the final dataset that is used for training and testing (Data Science PM, 2024). This project involves transforming all APIMS, METMalaysia, and NASA FIRMS timestamps into a uniform Malaysia Time (MYT, UTC+8) format and aggregating the number of FIRMS hotspots within the Malaysia bounding box. The result of this step is a combined hourly dataset that is ready for model training.

#### 3.2.3.4 Data Modelling

The modelling process uses appropriate methods to construct prediction models. It involves selecting a method, training models, parameter adjustments, and output generation. This stage focuses on developing models that learn helpful patterns from the prepared data (Schröer et al., 2021). In this project, this step uses a short-term forecasting model trained on the combined APIMS, METMalaysia, and FIRMS data to make predictions of API levels ranging from 1 to 24 hours ahead. The model inputs include weather conditions such as wind speed, humidity, rainfall, and hotspot intensity to enhance prediction accuracy.

#### 3.2.3.5 Data Evaluation

The evaluation phase compares the model outcomes with the project objectives. It also evaluates performance based on measurements and evaluates the usefulness and reliability of the output. In general, this stage determines limitations and pre-deployment preparation (Data Science PM, 2024). This project involves the forecasting model, which is tested on its ability to predict API threshold crossings, especially during haze periods. The test also verifies that the pipeline yields consistent results during normal days and haze periods before the system is deployed to the dashboard.

#### 3.2.3.6 Deployment

The final phase makes the project results accessible to users. It involves the implementation of the model within a working system (Data Science PM, 2024). It also includes setting up updates and long-term support. This stage prepares the solution for future use. Project deployment will involve connecting the trained model to the FastAPI backend, which will constantly fetch, clean, and serve new data predictions to the HTML dashboard. It also has an offline-friendly mode that shows the most recently cached data and the last update date to make the system remain useful even when network connectivity is poor.

---

## 3.3 Data Collection

This project gathers information from three internet sources. The main source is the air quality platform of Department of Environment Malaysia (APIMS), which contains the primary air quality indicators used for monitoring and forecasting. The second source is METMalaysia, which gives weather conditions including wind, humidity, rainfall, and temperature. The third source is NASA FIRMS, which gives real-time active fire and hotspot signals. All gathered information is provided in JSON format and stored as raw records before cleaning.

*Table 5: Dataset Name, Source, and Format from three datasets*

| Dataset Name | Source | Data Format |
|---|---|---|
| APIMS_air_quality_readings | https://eqms.doe.gov.my/APIMS/main | JSON |
| METMalaysia_Weather_Data | https://www.met.gov.my/ | JSON |
| NASAFIRMS_Fire_hotspot_data | https://firms.modaps.eosdis.nasa.gov/map/ | JSON |

---

## 3.4 Initial Data Pre-processing and Data Understanding

### 3.4.1 Data Pre-processing

During this step, the raw data of APIMS, METMalaysia, and NASA FIRMS is transformed to ensure the data can be combined into a single dataset. This phase involves the elimination of duplicates, converting timestamps to a single Malaysia time format, standardization of location names, removal of missing values, and aligning data to hourly records. Hotspot data is also summarized into useful features like the number of hotspots around a given place at a given time, to enable it to be combined with the air quality and weather data.

#### Import Data — APIMS

*Figure 19: Import APIMS libraries*
Loads the httpx, pandas, and FastAPI libraries to request the data.

*Figure 20: APIMS endpoint*
Stores the full endpoint link of APIMS that will be called to download the current station readings in JSON format.

*Figure 21: FastAPI application*
Creates the FastAPI application for the data and prepares two variables to hold the latest cleaned table and the last update time.

*Figure 22: Fetch APIMS*
Sends an online request to the APIMS endpoint and returns the response as JSON.

#### Import Data — METMalaysia

*Figure 23: Import METMalaysia libraries*
Imports libraries to load and preprocess data of METMalaysia.

*Figure 24: METMalaysia endpoint*
Contains the full endpoint link of METMalaysia that will be called to download the current station readings in JSON format and modify the time to align all timestamps to MYT.

*Figure 25: FastAPI app for METMalaysia and 2 new variables*
Generates two variables to store the most recent cleaned table and the most recent update time, and creates the FastAPI application for the data.

*Figure 26: Fetch METMalaysia data*
Sends an online request to the METMalaysia endpoint and receives the response as JSON format.

#### Import Data — NASA FIRMS

*Figure 27: Import NASAFirms libraries*
Imports the libraries to load and preprocess data of NASA FIRMS.

*Figure 28: NASAFirms endpoint*
Includes the NASA FIRMS endpoint link that will be used to get the current station readings in JSON format and adjust the time so that all timestamps are in line with MYT.

*Figure 29: NASAFirms FastAPI app and 2 variables*
Sets up the FastAPI application for data and generates two variables to contain the most recent cleaned table and update time.

*Figure 30: Fetch NASAFirms data*
Sends a request to the NASA FIRMS endpoint and receives a JSON response.

#### Preprocess Data — APIMS

*Figure 31: Preprocess APIMS JSON*
This function takes raw JSON data and extracts the attributes from each feature. It turns them into a pandas DataFrame format.

*Figure 32: Keeps selected APIMS columns*
Keeps only selected important columns from the DataFrame and removes the rest.

*Figure 33: APIMS Time Conversion*
Converts DATETIME to a normal readable date and time format.

*Figure 34: Standardize APIMS columns*
Standardizes text columns by converting the values to strings and removing extra spaces.

*Figure 35: Handle APIMS duplicate rows*
Removes duplicate rows where the STATION_ID and DATETIME column values are the same.

*Figure 36: Ensure numeric types on selected APIMS columns*
Converts API, API_PM10, LONGITUDE, and LATITUDE columns to numeric type to prevent errors.

*Table 6: APIMS information and description*

| Data | Output | Description/Explanation |
|------|--------|------------------------|
| APIMS | Figure 37: APIMS information | The output shows that the dataset contains 68 rows and 12 columns, with most columns fully complete except API_PM10, which is entirely missing for all 68 records. All data was recorded at the same timestamp, and the API readings range from 16 to 82 with an average of 46.72, where 37 records are classified as Moderate and 31 as Good. |

#### Preprocess Data — METMalaysia

*Figure 38: Preprocess METMalaysia JSON*
Checks if the API response is a list; otherwise raises an error.

*Figure 39: Turn JSON to DataFrame*
Converts raw JSON list to pandas DataFrame.

*Figure 40: Rename METMalaysia columns*
Renames the fields into clearer column names.

*Figure 41: Parse METMalaysia timestamp*
Parses the UTC timestamp and converts it to both UTC datetime and MYT.

*Figure 42: Remove METMalaysia degree symbol rows*
Removes degree symbol from temperature values and converts them to numeric numbers.

*Figure 43: Count METMalaysia rainy forecast slots*
Counts how many time slots in the rainfall forecast contain the word "hujan".

*Figure 44: Convert METMalaysia rainfall dict to string*
Converts rainfall forecast dictionaries to strings.

*Figure 45: Remove METMalaysia duplicate rows*
Removes duplicate rows.

*Figure 46: Reset METMalaysia DataFrame index*
Resets the DataFrame index to ensure the order is correct.

*Table 7: METMalaysia information and description*

| Data | Output | Description/Explanation |
|------|--------|------------------------|
| METMalaysia | Figure 47: METMalaysia information | METMalaysia data has 11 columns with 16 entries. Most columns are fully complete with no missing values. It also includes station details, raw timestamp, temperature, state, weather forecast, weather icon, UTC and MYT datetime, temperature in Celsius, and the number of rain forecast slots. The preview shows the first 5 rows for reference, with stations such as Kuala Lumpur, Kuching, Kota Kinabalu, Labuan, and Kangar. |

#### Preprocess Data — NASA FIRMS

*Figure 48: Preprocess NASAFirms*
Reads NASA FIRMS CSV to pandas DataFrame; otherwise returns an empty DataFrame with a message.

*Figure 49: Standardize NASAFirms columns*
Converts all column names to uppercase and removes extra spaces.

*Figure 50: Keep selected NASAFirms columns*
Keeps only selected hotspot-related columns.

*Figure 51: Combine NASAFirms acquisition date and time*
Combines ACQ_DATE and ACQ_TIME into UTC and MYT.

*Figure 52: Remove original NASAFirms date and time columns*
Deletes old ACQ_DATE and ACQ_TIME since they are no longer needed.

*Figure 53: Convert selected columns into numeric format*
Converts measurement columns into numeric format.

*Figure 54: Filter NASAFirms hotspot records*
Keeps only hotspot records whose latitude and longitude fall within the predefined Malaysia area.

*Figure 55: Rename NASAFirms columns*
Renames some columns for better readability.

*Figure 56: Remove NASAFirms duplicate rows*
Removes duplicate rows if any.

*Figure 57: Reset NASAFirms index*
Resets row numbering after cleaning to ensure the order is correct.

*Table 8: NASAFirms information and description*

| Data | Output | Description/Explanation |
|------|--------|------------------------|
| NASA FIRMS | Figure 58: NASAFirms information | NASA FIRMS dataset has 12 columns with 26 entries. All columns are complete with no missing values. It also includes latitude, longitude, brightness values, FRP, confidence, scan, track, satellite, day/night status, and UTC and MYT acquisition datetime columns. The preview shows the first 5 rows for reference, and the cleaned NASA FIRMS data remains at 26 rows and 12 columns. |

---

### 3.4.2 Data Understanding

In this project, data understanding aims to verify the data source and the fields required in the pipeline. APIMS is checked to ensure that the air quality output fields and the time of update are correct. METMalaysia is analysed to ensure weather fields and forecast timestamps are present. NASA FIRMS is checked to ensure that hotspot location fields and detection time fields are present. Simple checks are conducted to detect missing values, unexpected zero values, time discrepancies, duplicated records, and incorrect location names. Overall, this step ensures whether the merged dataset contains sufficient continuous hourly records to provide one-to-24-hour forecasting.

#### 3.4.2.1 APIMS

*Figure 59: APIMS total rows, columns and first 5 rows*
Prints the total rows and columns of the data, followed by the first 5 records.

*Figure 60: Description of APIMS data*
Shows statistical summary of all columns.

*Figure 61: APIMS unique value count*
Counts the total number of different values in each column and sorts them from highest to lowest.

*Table 9: APIMS attributes and observations*

| Attribute | Observation |
|-----------|-------------|
| STATION_ID | 68 unique IDs (each station appears to have a distinct ID). |
| LATITUDE | 68 unique values (likely one latitude per station). |
| STATION_LOCATION | 68 unique values (unique location label per station). |
| LONGITUDE | 68 unique values (likely one longitude per station). |
| API | 37 unique values (API readings vary across stations/records). |
| STATE_NAME | 16 unique values (stations span 16 states). |
| REGION_NAME | 7 unique values (stations grouped into 7 regions). |
| STATION_CATEGORY | 6 unique values (6 station categories). |
| CLASS | 2 unique values (binary class grouping). |
| DATETIME | 1 unique value (all records share the same timestamp in this dataset snapshot). |
| API_PM10 | 1 unique value (PM10 API value constant in this snapshot). |
| PARAM_SELECTED | 1 unique value (only one parameter was selected for this snapshot). |

*Figure 63: Histogram of API Distribution*

The histogram indicates the distribution of the API readings of all the stations in the dataset. Most of the values are clustered in the middle (approximately between 45–65), with the highest bars being close to the mid-high 50s. This implies that, at this snapshot moment, numerous monitoring stations are reporting similar moderate API levels, not evenly distributed between very low and very high pollution levels.

Simultaneously, the shape is not symmetrical since there are smaller clusters of stations at the lower end (around 18–35) and few stations at the high end (around 75–85). It implies that air quality does not occur in the same way across the country — there are certain places where it is significantly cleaner and others where it is worsening. This distribution will assist users in determining the "normal" API level, whether the data is skewed, and whether there are any high-API stations worth further investigation.

*Figure 64: Correlation Heatmap*

The correlation heatmap summarizes linear relationships between numeric fields (API, API_PM10, LONGITUDE, LATITUDE). The most significant trend is a negative correlation between API and LONGITUDE (approximately −0.77). It indicates that the higher the longitude of a station, the lower the API value in the data. This correlation is not a cause-and-effect relationship — longitude does not cause pollution directly. It is mostly a geographical proxy, with different regions along the longitude axis being in different pollution circumstances at the same time.

Subsequently, the rest of the relationships are weak. API is only slightly positively correlated with LATITUDE (~0.10), and LONGITUDE with LATITUDE is virtually zero (~0.01), meaning there is not much linear dependency between these attributes. The empty column for API_PM10 normally occurs when the column has no values or invalid numeric values, so correlation cannot be calculated reliably.

#### 3.4.2.2 METMalaysia

*Figure 65: METMalaysia total rows, columns, and the first five records*
Prints the first five entries after printing the total number of rows and columns in the data.

*Figure 66: Description of METMalaysia data*
Displays a statistical summary for every column.

*Figure 67: METMalaysia unique value count*
Determines the total number of distinct values in each column and arranges them in ascending order.

*Table 10: METMalaysia attributes and observations*

| Attribute | Observation |
|-----------|-------------|
| STATION_NAME | 16 unique values (each record appears to represent a different station name). |
| STATE | 16 unique values (stations span 16 state labels). |
| STATION_CODE | 15 unique values (one station code appears more than once in this snapshot). |
| TEMPERATURE_RAW | 8 unique values (raw temperature readings vary across stations). |
| RAINFALL_FORECAST | 8 unique values (forecasted rainfall values vary across records). |
| TEMPERATURE_C | 8 unique values (temperature in °C varies across records). |
| RAIN_FORECAST_SLOTS | 6 unique values (the number of rainy forecast slots differs by station). |
| WEATHER_ICON | 2 unique values (weather conditions are grouped into 2 icon categories). |
| TIMESTAMP_RAW | 1 unique value (all records share the same raw timestamp in this dataset snapshot). |
| DATETIME_MYT | 1 unique value (all records share the same MYT datetime in this dataset snapshot). |
| DATETIME_UTC | 1 unique value (all records share the same UTC datetime in this dataset snapshot). |

*Figure 69: Distribution of Temperature Histogram*

The histogram indicates that temperature values at the weather stations are concentrated in the 25°C to 28°C range. It is in line with normal weather conditions in Malaysia — that is, tropical weather at the time of this snapshot. Having only 4 distinct temperature values across 16 stations demonstrates that several stations have the same readings, showing how similar daytime temperatures are across states at the same hour. The cluster has a red dashed mean line showing the average temperature of 26°C.

This implies that temperature alone might not be a good differentiating factor between states at a single snapshot. Over time, with morning, afternoon, and night readings, the change will be more significant as a forecasting characteristic. Temperature has a direct effect on the behaviour of air pollutants — hotter air at the surface can trap pollutants at the ground level through temperature inversion, whereas cooler air can permit greater vertical mixing. Overall, it remains a beneficial input variable to the API forecasting model.

*Figure 70: Bar Chart of Avg Rain Forecast Slots per State*

The bar chart shows that most states indicate 0 rainy forecast slots. This means that forecast rainfall is concentrated in few states rather than spread across a large area in Malaysia. The difference between states (represented by 6 distinct values of RAIN_FORECAST_SLOTS) is significant since rainfall is among the most potent natural processes that decrease air pollution. Physically, rain carries PM2.5 and other particulate matter out of the air, resulting in a decrease in API readings, occasionally by a significant margin within a short period.

From a pipeline perspective, this chart ensures that RAIN_FORECAST_SLOTS is a variable with sufficient spread across states to be useful as a feature in the forecasting model. States with zero rain slots may experience less natural pollutant removal and may be more susceptible to API spikes, particularly when fire hotspot activity is observed by NASA FIRMS. These two signals — rain forecast and fire intensity — are combined to form the central weather-fire interaction logic upon which the system produces cause explanations on the dashboard.

#### 3.4.2.3 NASA FIRMS

*Figure 71: NASAFirms total rows, columns, and the first five rows*
Prints the data's total rows and columns, followed by the first five records.

*Figure 72: Description of NASAFirms data*
Displays statistical summary for every column.

*Figure 73: NASAFirms unique value count*
Evaluates how many different values exist in each column and arranges them from highest to lowest.

*Table 11: NASAFirms attributes and observations*

| Attribute | Observation |
|-----------|-------------|
| LATITUDE | 26 unique values (each record has a distinct latitude coordinate). |
| LONGITUDE | 26 unique values (each record has a distinct longitude coordinate). |
| BRIGHTNESS_TI4_K | 26 unique values (brightness varies across all detected points). |
| BRIGHTNESS_TI5_K | 26 unique values (secondary brightness also varies across all detected points). |
| FRP_MW | 24 unique values (fire radiative power varies, with a few repeated readings). |
| SCAN_KM | 15 unique values (scan width differs across detections). |
| TRACK_KM | 13 unique values (track length varies across detections). |
| CONFIDENCE | 3 unique values (confidence is grouped into three categories). |
| SATELLITE | 1 unique value (all records were captured by the same satellite). |
| DAYNIGHT | 1 unique value (all records were captured during the same day/night condition). |
| ACQ_DATETIME_UTC | 2 unique values (detections were recorded at two UTC timestamps). |
| ACQ_DATETIME_MYT | 2 unique values (detections were recorded at two MYT timestamps). |

*Figure 75: Distribution of FRP Histogram*

The histogram indicates a heavily right-skewed distribution with the majority of 26 identified hotspots having FRP values less than 10 MW, and a few higher records further along the right tail as outliers. The form is typical of actual fire data — most identified hotspots are small, weak fires like agricultural clearing. The outliers are the high-radiative, high-intensity fires that can cause heavy columns of smoke to drift across state lines and impact air quality at APIMS monitoring stations. The mean line is significantly to the right of the highest bars, proving that the average is being drawn upwards by high-FRP outliers.

In the forecasting model context, this distribution is an important data point. It implies that FRP_MW_MEAN as a feature alone might be insufficient during quiet periods when most fires are small. This is the reason FRP_MW_MAX is also included in the merged dataset — to capture those high-intensity outlier events that may contribute to haze events. The skewed distribution justifies the choice of monitoring both the average and maximum fire intensity per hour.

*Figure 76: Bar Chart of Hotspot Count by Confidence Level*

The bar chart indicates that most of the 26 identified hotspots are in the nominal confidence category. High-confidence and low-confidence detections are equal in number. This distribution supports the quality of data. Most fire observations in this snapshot are considered valid by the VIIRS sensor system, with a very small fraction deemed potentially uncertain. Confidence in FIRMS data is determined by brightness temperature thresholds, comparison of background temperature, and contextual checks — a nominal or high rating implies that the thermal anomaly observed is more likely a real fire.

From the pipeline viewpoint, this breakdown of confidence tells us about the behaviour of the HIGH_CONF_COUNT feature in the combined data. When the number or proportion of high-confidence hotspots is higher, the fire signal sent to the model is more reliable. The low-confidence fraction is not completely ignored but is instead stored in the total HOTSPOT_COUNT, as even uncertain detections in an area with known fire history can be useful predictively when combined with wind direction and weather data.

*Figure 77: Hotspot Geographic Distribution Heatmap*

The scatter plot shows the identified hotspots in the Malaysia bounding box by longitude and latitude, with each point coloured and sized based on its FRP_MW value. The spatial distribution briefly shows that the hotspots are not evenly distributed in the study area. Some hotspots appear clustered in certain longitude and latitude areas, which may correspond to fire-prone areas. The biggest and darkest-coloured points indicate the high-FRP outliers; their geographic location shows which areas recorded the strongest fires during the period.

This chart represents the link between fire data and the spatial area of the APIMS monitoring network. Identifying intense fire locations relative to APIMS station coordinates makes it easier to identify which monitoring stations may be downwind of fire activity, potentially causing higher API readings than usual. Although the existing pipeline consolidates fires on a national scale on an hourly basis, this scatter plot provides a basis for possible future improvement where hotspot proximity and wind direction may be utilized to estimate fire impact more accurately for individual stations.

---

## 3.5 Data Merge

In this phase, the three datasets that have been imported, pre-processed, and visualized are merged to support the objectives and goals of the project.

*Figure 78: Loads three preprocessing models*
Loads all three preprocessing models from the same directory.

*Figure 79: Select APIMS columns*
Keeps the essential APIMS columns needed.

*Figure 80: Select METMalaysia columns*
Retains only the state, datetime, temperature, and rainfall columns from METMalaysia data.

*Figure 81: Select NASAFirms columns*
Extracts only acquisition time, fire radiative power, and confidence level from FIRMS data.

*Figure 82: Round to Hour*
Floors the datetime series to the nearest hour so the three datasets share the same time.

*Figure 83: Aggregate NASAFirms hourly*
Collapses all individual hotspot rows into one fire summary per hour with count, mean, max intensity, and high confidence count.

*Figure 84: Clean States*
Strips "w.p.", " wp ", "w.p, ", and "wilayah persekutuan" prefixes and lowercases state names so APIMS and METMalaysia labels match correctly.

*Figure 85: Merge all datasets*
Begins the merge_all function by selecting the relevant columns from all three datasets.

*Figure 86: Rounds APIMS and METMalaysia time*
Rounds APIMS and METMalaysia timestamps to the nearest hour.

*Figure 87: Applies clean state for APIMS and METMalaysia*
Applies clean state to normalise state names for APIMS and METMalaysia.

*Figure 88: Creates empty FIRMS hourly placeholder*
Creates an empty FIRMS hourly placeholder if no fire data is available; otherwise aggregates it.

*Figure 89: Left joins APIMS with METMalaysia*
Left joins APIMS with METMalaysia on matching state and hour.

*Figure 90: Left joins merged table with hourly NASAFirms*
Left joins the merged table with the hourly FIRMS fire summary on hour.

*Figure 91: Fills missing NASAFirms columns*
Fills all missing FIRMS columns with 0 to represent hours with no fire activity.

*Figure 92: Drops selected columns*
Drops the temporary helper columns because they are no longer needed.

*Figure 93: Sorts the table and resets index*
Sorts the final table by station and hour and resets the index.

*Table 12: Merged Data attributes, observations, and functions*

| Attribute | Observation | Function |
|-----------|-------------|----------|
| STATION_ID | 68 unique values; each record maps to one distinct monitoring station. | Used to group and track readings per station over time. |
| STATION_LOCATION | 68 unique values; represents the station name. | Helps interpret which physical location the API reading belongs to. |
| STATE_NAME | 16 unique values; covers all Malaysian states. | Used to match APIMS readings with METMalaysia weather data by state. |
| LATITUDE | 68 unique values; each station has a distinct latitude coordinate. | Captures geographic position of each monitoring station. |
| LONGITUDE | 68 unique values; each station has a distinct longitude coordinate. | Captures geographic position of each monitoring station. |
| API | 38 unique values ranging from 18 (min) to 76 (max), mean ≈ 51.5. | Represents the air pollutant index. |
| CLASS | 2 unique values: Good (23 rows) and Moderate (45 rows). No unhealthy readings. | Categorises API into health-based bands. |
| HOUR_MYT | 1 unique value (2026-03-11 21:00:00). All rows are from the same hour. | Used to align APIMS, METMalaysia, and FIRMS data to the same hour. |
| TEMPERATURE_C | 5 unique values ranging from 26°C (min) to 30°C (max), mean ≈ 27.3°C. | Temperature affects how pollutants disperse in the atmosphere. |
| RAIN_FORECAST_SLOTS | 9 unique values ranging from 0 (min) to 19 (max), mean ≈ 5.5. | Rainfall washes out PM2.5 particles, directly lowering API. |
| HOTSPOT_COUNT | 1 unique value (0.0). No active fire hotspots detected in Malaysia at this hour. | Total number of NASA FIRMS hotspots detected nationally per hour. |

---

## 3.6 Summary

In summary, this chapter introduced the methodology which will be used to develop the project based on the CRISP-DM framework. It begins with translating the project aim into clear requirements, followed by data understanding and data preparation, and then model development and deployment. It outlined the approach that the project will take in dealing with multi-source real-time data by collaborating with the primary air quality signal of APIMS and the complementary signals of METMalaysia and NASA FIRMS, because these sources are required to constitute a single dataset that is conducive to short-term prediction and description.

Moreover, this chapter presented the intended data collection process and initial preprocessing strategy, including cleaning and standardization of the retrieved API data, and initial data understanding measures such as summary statistics, counts of unique values, and basic visual inspection to verify the data structure and prepare it for the subsequent step. The methodology is also justified, and the work done in preparation is correlated to the generation of credible model inputs and deployable system outputs. The following chapter will be the conclusion of the investigation report, examining what has been determined so far and outlining the main limitations and recommendations on how to proceed with the remaining implementation phases.

---

# Chapter 4: Conclusion

## 4.1 Critical Evaluation

The initial stage of the project has reached a distinct and viable basis for the entire system. The project direction has already been set by the investigation as a real-time web-based nowcasting application in Malaysia that integrates APIMS air quality measurements, METMalaysia weather, and NASA FIRMS fire hotspot signals. In addition, it aligns with the blueprint plan of constructing an end-to-end data retrieval pipeline — from cleaning, time and location alignment, merging, and feature building, to forecasting, alerts, explanation, and user interface. It also validates the system concept and tools early, such as HTML for the UI and FastAPI for the backend services.

In terms of technical development, the project has already shown that real-time APIMS readings can be fetched, standardised, deduplicated, and explored with reliable data understanding outputs (describe tables, unique counts, and two key visualisations). This is a significant step since APIMS is the key target signal that the system monitors and predicts, and the APIMS data structure is the anchor that aligns METMalaysia and FIRMS. Simultaneously, it ensures that the system is built to support real-time monitoring graphs, short-term forecasts, alert outputs, and an offline mode which displays the last saved data and last updated time when the internet is weak.

---

## 4.2 Limitation

Even though the project is on its way to achieving its goals, there are a number of limitations encountered at the current level. To start with, the implementation that is currently in place has primarily tested the APIMS current reading endpoint and basic preprocessing, but the entire multi-source integration is not yet finished. The pipeline remains unstable in terms of APIMS, METMalaysia weather, and NASA FIRMS hotspot alignment by time and location, and incomplete alignment can cause inconsistent features and lower forecasting reliability. Moreover, the existing dataset access is snapshot-based, so sufficient time series gathering is still necessary to enable 1-to-24-hour forecasting and to compare performance on normal days versus haze episodes.

Second, analysis may be impacted by data quality and coverage limitations. Pollutant-specific fields may have missing values or different reporting between stations, which can decrease the utility of correlation analysis and model training. Only numerical station coordinates are available, which are not useful in interpreting local conditions due to the possibility that land use, traffic density, and industrial areas influence pollution but are not directly measured. On the system side, real-time updates can be network-unstable, throttled by API, or offline. Overall, this can decrease the precision of live monitoring unless caching and retry logic are fully optimized.

---

## 4.3 Recommendation

To strengthen the project further and minimize the limitations, several improvements are suggested. It is essential to first complete the multi-source data fusion as specified in the blueprint through a uniform alignment strategy. This includes timestamp normalization, nearest station/region-based joining rules, and hotspot aggregation logic such as hotspot counts within a radius and upwind filtering based on wind direction. It should also be equipped with a planned data collection procedure to create a historic time series dataset that can be used to make forecasts and conduct adequate assessments, such as testing during hazy conditions and abnormal weather.

Furthermore, to enhance model reliability, interpretability, and system scalability: compare simple baseline models with more sophisticated methods when sufficient history is available; include explainability results that give users a simple summary of how predicted spikes relate to weather and hotspot evidence; add data validation tests for impossible values, sharp rises, and level values; and use missing value processing rules prior to feature engineering.

For deployment, add asynchronous processing, caching, and retry mechanisms to ensure that the dashboard can be used even when the network is unavailable or the load is high, and investigate cloud deployment when the load is high. These improvements will make the system stronger, easier to comprehend, and more effective in supporting health-related decisions.

---

# References

MyEQMS. (n.d.). https://eqms.doe.gov.my/APIMS/main

Feldscher, K. (2025, February 25). The dangers of air pollution for heart health. *Harvard T.H. Chan School of Public Health.* https://hsph.harvard.edu/news/the-dangers-of-air-pollution-for-heart-health/

Naeem, A., & Silveyra, P. (2019). Sex Differences in Paediatric and Adult Asthma. *European Medical Journal (Chelmsford, England), 4*(2), 27. https://pmc.ncbi.nlm.nih.gov/articles/PMC6641536/

Coskuner, K. A., et al. (2022). Assessing the performance of MODIS and VIIRS active fire products in the monitoring of wildfires: a case study in Turkey. *iForest - Biogeosciences and Forestry, 15*(2), 85–94. https://doi.org/10.3832/ifor3754-015

Houdou, A., et al. (2024). Interpretable Machine Learning Approaches for Forecasting and Predicting Air Pollution: A Systematic review. *Aerosol and Air Quality Research, 24*(1), 230151. https://doi.org/10.4209/aaqr.230151

Hope, E. S., et al. (2024). Exploring the use of satellite Earth observation active wildland fire hotspot data via open access web platforms. *International Journal of Digital Earth, 17*(1). https://doi.org/10.1080/17538947.2024.2420821

Lu, H., et al. (2025). The contribution of fires to PM2.5 and population exposure in the Asia Pacific region. *Atmospheric Chemistry and Physics, 25*(17), 10141–10158. https://doi.org/10.5194/acp-25-10141-2025

Mohd Zulkifli, S. W. H., et al. (2024). Association between PM10 and respiratory diseases admission in peninsula Malaysia during haze. *Scientific Reports, 14*(1). https://doi.org/10.1038/s41598-024-63591-x

Nguyen, L. S. P., et al. (2022). Trans-boundary air pollution in a Southeast Asian megacity: Case studies of the synoptic meteorological mechanisms and impacts on air quality. *Atmospheric Pollution Research, 13*(4), 101366. https://doi.org/10.1016/j.apr.2022.101366

Park, Y. H., et al. (2023). Evaluation of an air quality warning system for vulnerable and susceptible individuals in South Korea: an interrupted time series analysis. *Epidemiology and Health.* https://doi.org/10.4178/epih.e2023020

Sofwan, N. M., et al. (2021). Risks of exposure to ambient air pollutants on the admission of respiratory and cardiovascular diseases in Kuala Lumpur. *Sustainable Cities and Society, 75*, 103390. https://doi.org/10.1016/j.scs.2021.103390

Tran et al. (2023). Forecasting hourly PM2.5 concentration with an optimized LSTM model. *Atmospheric Environment, 315*, 120161–120161. https://doi.org/10.1016/j.atmosenv.2023.120161

United Nations. (2024). *The Sustainable Development Goals Report 2024* (pp. 1–51). https://unstats.un.org/sdgs/report/2024/The-Sustainable-Development-Goals-Report-2024.pdf

World Health Organization. (2024, October 24). Ambient (outdoor) air pollution. https://www.who.int/news-room/fact-sheets/detail/ambient-%28outdoor%29-air-quality-and-health

World Health Organization. (2026). https://iris.who.int/server/api/core/bitstreams/75c3b348-9c28-4269-8e08-0f45c6791206/content

Zhang, Y., et al. (2025). Misleading air quality reports lower the public's perception of pollution and increase travel behavior. *Communications Earth & Environment, 6*(1). https://doi.org/10.1038/s43247-025-02670-x

Ritchie, H., & Roser, M. (2024, February). Air Pollution. *Our World in Data.* https://ourworldindata.org/air-pollution

Rahman et al. (2022). Assessment of PM2.5 patterns in Malaysia using the clustering method. *Aerosol and Air Quality Research, 22*(1), 210161. https://doi.org/10.4209/aaqr.210161

RTM. (2023). Portal Berita RTM. https://berita.rtm.gov.my/nasional/senarai-berita-nasional/senarai-artikel/tutup-sekolah-serta-merta-jika-catatan-ipu-lebih-200/

Department of Environment Malaysia. (2025). Jabatan Alam Sekitar – Kementerian Alam Sekitar dan Air. https://www.doe.gov.my/

Nguyen et al. (2024). An exploration of meteorological effects on PM2.5 air quality in several provinces and cities in Vietnam. *Journal of Environmental Sciences, 145*, 139–151. https://doi.org/10.1016/j.jes.2023.07.020

METMalaysia. (2025). https://api.met.gov.my/

Davies, D., et al. (2019). NASA's Fire Information for Resource Management System (FIRMS): Near Real-Time Global Fire Monitoring Using Data from MODIS and VIIRS. https://ntrs.nasa.gov/citations/20190032007

Rahman et al. (2023). Forecasting PM2.5 in Malaysia Using a Hybrid Model. *Aerosol and Air Quality Research, 23*(9), 230006. https://doi.org/10.4209/aaqr.230006

Visual Studio Code. (2023). Documentation for Visual Studio Code. https://code.visualstudio.com/docs

Microsoft Team. (2024, January 31). Windows 11 overview for administrators. https://learn.microsoft.com/en-us/windows/whats-new/windows-11-overview

Awang, M. B., Jaafar, A. B., Abdullah, A. M., Ismail, M. B., Hassan, M. N., Abdullah, R., Johan, S., & Noor, H. (2000). Air quality in Malaysia: Impacts, management issues and future challenges. *Respirology, 5*(2), 183–196. https://doi.org/10.1046/j.1440-1843.2000.00248.x

Sigsgaard, T., & Hoffmann, B. (2024). Assessing the health burden from air pollution. *Science, 384*(6691), 33–34. https://doi.org/10.1126/science.abo3801

Zhou, Y., Zhang, X., Zhang, C., Chen, B., & Gu, B. (2024). Mitigating air pollution benefits multiple sustainable development goals in China. *Environmental Pollution*, 123992–123992. https://doi.org/10.1016/j.envpol.2024.123992

Shazia Iram, Iqra Qaisar, Shabbir, R., Muhammad Saleem Pomme, Schmidt, M., & Hertig, E. (2025). Impact of Air Pollution and Smog on Human Health in Pakistan: A Systematic Review. *Environments, 12*(2), 46–46. https://doi.org/10.3390/environments12020046

Sokhi, R., Moussiopoulos, N., Baklanov, A., Bartzis, J., Coll, I., Finardi, S., Friedrich, R., Geels, C., Grönholm, T., Halenka, T., Ketzel, M., Maragkidou, A., Matthias, V., Moldanova, J., Ntziachristos, L., Schäfer, K., Suppan, P., Tsegas, G., Carmichael, G., & Franco, V. (2022). Advances in Air Quality Research – Current and Emerging Challenges. *Atmos. Chem. Phys., 22*(7), 4615–4703. https://doi.org/10.5194/acp-22-4615-2022

Luo, C., Qian, J., Liu, Y., Qiang Lv, Ma, Y., & Yin, F. (2022). Long-term air pollution levels modify the relationships between short-term exposure to meteorological factors, air pollution and the incidence of hand, foot and mouth disease in children: a DLNM-based multicity time series study in Sichuan Province, China. *BMC Public Health, 22*(1). https://doi.org/10.1186/s12889-022-13890-7

Rus, A.-A., & Mornoş, C. (2022). The Impact of Meteorological Factors and Air Pollutants on Acute Coronary Syndrome. *Current Cardiology Reports.* https://doi.org/10.1007/s11886-022-01759-5

Ulpiani, G., Duhirwe, P. N., Yun, G. Y., & Lipson, M. J. (2022). Meteorological influence on forecasting urban pollutants: Long-term predictability versus extreme events in a spatially heterogeneous urban ecosystem. *Science of the Total Environment, 814*, 152537. https://doi.org/10.1016/j.scitotenv.2021.152537

Lu, C.-W., Fu, J., Liu, X.-F., Chen, W.-W., Hao, J.-L., Li, X.-L., & Pant, O. P. (2021). Air pollution and meteorological conditions significantly contribute to the worsening of allergic conjunctivitis: a regional 20-city, 5-year study in Northeast China. *Light: Science & Applications, 10*(1). https://doi.org/10.1038/s41377-021-00630-6

Sritong-aon, C., Thomya, J., Kertpromphan, C., & Phosri, A. (2021). Estimated effects of meteorological factors and fire hotspots on ambient particulate matter in the northern region of Thailand. *Air Quality, Atmosphere & Health, 14*(11), 1857–1868. https://doi.org/10.1007/s11869-021-01059-x

Sumaryati, Andarini, D. F., Cholianawati, N., & Indrawati, A. (2022). Smoke propagation during fire in Kalimantan and Sumatra in 2015 and 2019. In *Springer proceedings in physics* (pp. 145–157). https://doi.org/10.1007/978-981-19-0308-3_11

Sarkar, A., Roy, D. G., & Datta, P. (2025). STAT-X: short-term atmospheric temperature forecasting using machine learning models with explainable-AI. *Theoretical and Applied Climatology, 156*(9). https://doi.org/10.1007/s00704-025-05693-8

Xie, Y., Pongsakornsathien, N., Gardi, A., & Sabatini, R. (2021). Explanation of Machine-Learning Solutions in Air-Traffic Management. *Aerospace, 8*(8), 224. https://doi.org/10.3390/aerospace8080224

Eik, M., Kose, A., Hokmabad, H. N., & Belikov, J. (2025). Explainable AI based System for Supply Air Temperature Forecast. *2025 IEEE PES Innovative Smart Grid Technologies Conference Europe (ISGT Europe)*, 1–5. https://doi.org/10.1109/isgteurope64741.2025.11305592

Schröer, C., Kruse, F., & Gómez, J. M. (2021). A Systematic Literature Review on Applying CRISP-DM Process Model. *Procedia Computer Science, 181*(1), 526–534.

Data Science PM. (2024, December 9). What Is CRISP DM? *Data Science Project Management.* https://www.datascience-pm.com/crisp-dm-2/

American Heart Association. (n.d.). Air pollution CVD and stroke statistics. https://newsroom.heart.org/file/infographic-numbers?action=

Hanin, W., Humaida Banu Samsudin, & Majid, N. (2023). Association between PM10 and respiratory diseases admission in Peninsular Malaysia during the haze. *Research Square.* https://doi.org/10.21203/rs.3.rs-3037064/v1

Livingasean. (2023, October 23). Air Quality around the ASEAN / Air Pollution in Bangkok, Hanoi and Jakarta. *LIVING ASEAN.* https://livingasean.com/explore/buzz/air-quality-asean-air-pollution-bangkok-hanoi-jakarta/

Rizwan, G. (2025, March 5). Air Quality Index (AQI). *C4S courses.* https://c4scourses.in/blog/air-quality-index-aqi/

Koala_on_a_Treadmill. (n.d.). NASA's map of active fires shows nearly a third of Africa on fire. https://www.reddit.com/r/geography/comments/15yd5kn/nasas_map_of_active_fires_shows_nearly_a_third_of/

Microsoft. (n.d.). Introducing Windows 11. https://news.microsoft.com/windows11-general-availability/

Minh, V. T. T., Tin, T. T., & Hien, T. T. (2021). PM2.5 Forecast System by Using Machine Learning and WRF Model, A Case Study: Ho Chi Minh City, Vietnam. *Aerosol and Air Quality Research, 21*(12), 210108. https://doi.org/10.4209/aaqr.210108

Chumbar, S. (2023, September 22). The CRISP-DM Process: A Comprehensive Guide. *Medium.* https://medium.com/@shawn.chumbar/the-crisp-dm-process-a-comprehensive-guide-4d893aecb151

---

# Appendices

## Appendix A: PPF – Project Title Proposal

*Figures 95–114: PPF – Project Title Proposal (20 pages)*

## Appendix B: Ethics Form (Fast Track)

*Figures 115–119: Fast Track Ethics Form (5 pages)*

## Appendix C: Log Sheets

*Figures 120–122: Log Sheets (3 pages)*

## Appendix D: Gantt Chart

*Figure 123: Gantt Chart*

## Appendix E: Turnitin Submission

*(See submitted document)*
