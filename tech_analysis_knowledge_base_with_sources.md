> 주의: 아래 출처는 각 기업 섹션의 사실 검증과 참고문헌 생성을 위해 추가한 링크입니다.
> 공식 홈페이지 중심으로 넣었고, 일부 투자·언론 정보는 외부 기사/기관 페이지를 함께 붙였습니다.

# 로보틱스 스타트업 기술력 분석 Knowledge Base
> 기술력 분석 에이전트 RAG 컬렉션 (`robotics_robotics`) 전용 문서  
> 평가 항목: 핵심 기술 독창성 / TRL / HW+SW 통합도 / DoF / Payload / 자율주행 레벨 / AI 알고리즘

---

## 1. Locus Robotics

### 하드웨어 스펙
| 모델 | Payload | 주행 속도 | 배터리 |
|---|---|---|---|
| Locus Origin | 36 kg | 보행 속도(~1.4 m/s) | 연속 14시간 |
| Locus Vector | 272 kg | - | - |
| Locus Max | 1,360 kg | - | - |

- **이동 방식**: 차동 구동(Differential Drive), Locus Vector는 전방향(Omnidirectional)
- **DoF**: 이동 자유도 3DoF (x, y, θ), 조작 기능 없음(피킹은 작업자가 수행)
- **센서**: LiDAR 기반 자연 랜드마크 항법, 카메라

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 2~3 (반자율 협동 피킹, 경로 계획 자율 수행)
- **SLAM**: LiDAR 기반 자연 특징점 SLAM
- **AI 알고리즘**: 경로 최적화, 군집 제어(수백 대 동시 운용)
- **플랫폼**: LocusOne — 이기종 로봇 통합 관제, WMS 연동, RaaS 구독 모델

### 기술 완성도
- **TRL**: 8~9 (글로벌 물류 현장 대규모 상용 배포 완료)
- **HW+SW 통합도**: 중간 (HW 자체 제작, SW 플랫폼 강점, 피킹은 인간 의존)
- **핵심 독창성**: 협동 피킹(Co-bot picking) + RaaS 구독 모델 결합
- **강점**: 검증된 레퍼런스, 빠른 ROI, 인프라 개조 불필요
- **약점**: 완전 무인화 불가, 작업자 상시 필요

---


### 출처
- Locus Robotics(2026). *Locus Robotics*. https://locusrobotics.com/
- Locus Robotics(2026). *Company*. https://locusrobotics.com/company
- Locus Robotics(2026). *Latest News & Press Releases*. https://locusrobotics.com/news
- Locus Robotics(2026). *Resource Library*. https://locusrobotics.com/resources

## 2. Exotec

### 하드웨어 스펙
| 모델 | 기능 | 주요 스펙 |
|---|---|---|
| Skypod | 3D 이동 로봇 | 최대 12m 수직 등반, 약 30 kg 토트 운반 |
| Skypicker | 로봇 팔 피킹 | 시간당 최대 600 picks, AI 비전 탑재 |
| Skypath | 모듈형 컨베이어 | 초당 2,500 토트 처리 |

- **이동 방식**: 3D 자율주행 (바닥 + 수직 선반 등반)
- **DoF**: 이동 6DoF(3D 공간 이동) + 로봇 팔 다축
- **센서**: 카메라, 장애물 회피 센서

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 4 (통제된 환경 완전 자율)
- **AI 알고리즘**: AI 비전 기반 피킹(Skypicker), 경로 최적화
- **플랫폼**: Deepsky — 실시간 데이터 분석, WMS 연동, 멀티 로봇 오케스트레이션

### 기술 완성도
- **TRL**: 8~9 (Uniqlo, Decathlon, Gap 등 글로벌 브랜드 실제 운용)
- **HW+SW 통합도**: 높음 (3D 이동 + 피킹 + 컨베이어 + SW 엔드투엔드 통합)
- **핵심 독창성**: 세계 최초 3D 수직 이동 AMR — 고밀도 저장 + 피킹 동시 구현
- **강점**: 공간 효율 극대화, 모듈식 확장, 설비 추가 투자 최소화
- **약점**: 초기 도입 비용 높음, 폐쇄형 그리드 환경 필요

---


### 출처
- Exotec(2026). *Exotec: Warehouse Automation Solutions*. https://www.exotec.com/
- Exotec(2026). *Who We Are*. https://www.exotec.com/company/
- Exotec(2024-07-16). *From Software to Hardware: Comprehensive Guide to Integrating Warehouse Robotics*. Exotec. https://www.exotec.com/insights/from-software-to-hardware-comprehensive-guide-to-integrating-warehouse-robotics/
- Exotec(2026). *Autonomous Mobile Robots for Warehouses*. https://www.exotec.com/system/automated-warehouse-robots/

## 3. Geek+

### 하드웨어 스펙
| 시리즈 | 모델 예시 | Payload |
|---|---|---|
| P-Series (피킹) | P500, P800, P1200 | 500~1,200 kg |
| S-Series (분류) | 바닥형/다층형 | - |
| 무인지게차 | - | 최대 3,000 kg |
| RoboShuttle | 토트-투-퍼슨 | - |

- **이동 방식**: 차동 구동, 전방향 이동
- **DoF**: 이동 3DoF + 로봇 팔 피킹 스테이션 다축
- **센서**: LiDAR, 카메라, IMU

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 4 (통제된 환경 완전 자율)
- **AI 알고리즘**: 강화학습 기반 스케줄링, 컴퓨터 비전 기반 비정형 물체 피킹
- **플랫폼**: Geek+ Brain — 수천 대 실시간 최적화, 로봇 팔 피킹 스테이션 통합

### 기술 완성도
- **TRL**: 9 (40개국 800개 이상 고객사, 2025년 HKEX 상장)
- **HW+SW 통합도**: 매우 높음 (풀 스펙트럼 HW 라인업 + AI 플랫폼 + RaaS)
- **핵심 독창성**: 가장 넓은 HW 라인업 × 강력한 AI 오케스트레이션 플랫폼
- **강점**: 검증된 규모, 수직 계열화, 완전 무인 창고 지향
- **약점**: 중국 기업 지정학적 리스크, 고객사 의존도 분산 필요

---


### 출처
- Geek+(2026). *Smart Logistics, Better World*. https://www.geekplus.com/en
- Geek+(2026). *Geek+ Korea*. https://www.geekplus.com/ko-kr/
- Geek+(2026). *Robotics Technology*. https://www.geekplus.com/ko/technology/robotics
- Geek+(2025-04-30). *P Series Models*. Geek+. https://www.geekplus.com/technology-detail-page/p-series

## 4. Covariant

### 하드웨어 스펙
- **하드웨어 직접 제조 없음** — 서드파티 로봇 팔(UR, FANUC 등)에 SW 탑재
- **그리퍼**: 하이브리드(진공 흡입 + 핑거) 방식 지원
- **처리 가능 중량**: 최대 수 kg 수준(낱개 피킹 최적화)

### 소프트웨어 및 AI
- **자율주행 레벨**: 해당 없음(고정형 피킹 스테이션)
- **핵심 AI**: Covariant Brain — 로봇 파운데이션 모델(RFM)
- **AI 알고리즘**:
  - RFM-1: 텍스트·비디오 기반 로봇 행동 모델 (대규모 언어/행동 모델)
  - 모델 프리(Model-free) 범용 피킹: 사전 학습 없이 수만 종 SKU 즉시 처리
  - 강화학습 + 모방학습 결합
- **플랫폼**: Covariant Brain — 하드웨어 독립적 이식 가능 AI 두뇌

### 기술 완성도
- **TRL**: 7~8 (아마존 인수 후 라이선스 운용, 상용 피킹 스테이션 배포)
- **HW+SW 통합도**: 낮음(HW 없음) → SW 기술력은 업계 최고 수준
- **핵심 독창성**: 로봇 파운데이션 모델(RFM) — GPT와 유사한 범용 로봇 두뇌
- **강점**: HW 무관 범용성, 아마존 라이선스로 기술 가치 입증, 학문적 권위(Pieter Abbeel)
- **약점**: HW 직접 제어 불가, Amazon 인수 후 독립성 불확실

---


### 출처
- Covariant(2026). *Powering the future of automation, today*. https://covariant.ai/
- Covariant(2026). *About Us*. https://covariant.ai/about-us/
- Covariant(2024-03-11). *RFM-1: Launching pad for billions of robots*. Covariant. https://covariant.ai/insights/introducing-rfm-1-giving-robots-human-like-reasoning-capabilities/
- Covariant(2026). *The Robots*. https://covariant.ai/insights/the-robots/

## 5. Agility Robotics

### 하드웨어 스펙 (Digit)
| 항목 | 스펙 |
|---|---|
| 형태 | 2족 보행 휴머노이드 |
| 신장 | 약 175 cm (성인 남성 수준) |
| 페이로드 | 약 16 kg (상자 단위 물류 작업) |
| 보행 속도 | ~1.5 m/s |
| 배터리 | 약 2~4시간 (작업 환경 따라 상이) |
| DoF | 20+ DoF (팔·다리·손목 포함) |

- **이동 방식**: 2족 보행 (동역학 기반, Cassie 연구 계보)
- **센서**: LiDAR, 스테레오 카메라, IMU

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 3~4 (물류 창고 반구조 환경 자율 보행 및 작업)
- **AI 알고리즘**: 강화학습 기반 보행 제어, 컴퓨터 비전 기반 물체 인식, 동역학 제어
- **특이사항**: Cassie(전신)로 100m 달리기 완주, 계단·경사 보행 검증

### 기술 완성도
- **TRL**: 7~8 (RoboFab 대량 생산 공장 가동, 아마존 창고 실무 테스트 진행)
- **HW+SW 통합도**: 높음 (자체 설계 휴머노이드 + 보행 AI 완전 수직 계열화)
- **핵심 독창성**: 물류 특화 최초 상용 휴머노이드, 기존 시설 개조 없이 즉시 투입
- **강점**: 인프라 변경 불필요, Amazon 투자·검증, 대량 생산 체제 구축
- **약점**: 배터리 런타임 짧음, 높은 단가, 아직 제한적 작업 범위

---


### 출처
- Agility Robotics(2026). *Agility Robotics*. https://www.agilityrobotics.com/
- Agility Robotics(2026). *Company*. https://www.agilityrobotics.com/company
- Agility Robotics(2026). *Industries*. https://www.agilityrobotics.com/industries
- Agility Robotics(2026-02-19). *Agility Robotics Announces Commercial Agreement with Toyota Motor Manufacturing Canada*. Agility Robotics. https://www.agilityrobotics.com/content/agility-robotics-announces-commercial-agreement-with-toyota-motor-manufacturing-canada

## 6. AutoStore

### 하드웨어 스펙
| 모델 | 특징 | 주요 스펙 |
|---|---|---|
| R5 (Red Line) | 범용 그리드 로봇 | 표준 속도, 범용성 |
| B1 (Black Line) | 고성능·고효율 | 고속, 에너지 효율 |

- **이동 방식**: 그리드 상단 XY 이동 (2D 평면)
- **DoF**: 2DoF 이동 + 수직 리프팅 1DoF
- **센서**: 그리드 내 위치 인식 센서
- **저장 밀도**: 기존 창고 대비 공간 효율 최대 4배

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 4 (폐쇄 그리드 환경 완전 자율)
- **AI 알고리즘**: 경로 최적화, 빈(Bin) 재배치 알고리즘
- **플랫폼**: Controller SW — 로봇·포트·그리드 통합 제어, WMS 연동

### 기술 완성도
- **TRL**: 9 (50개국 1,200+ 시스템, 오슬로 상장, SoftBank 28억 달러 투자)
- **HW+SW 통합도**: 높음 (폐쇄형 생태계 완전 통합)
- **핵심 독창성**: Cube Storage Automation 세계 최초 개발·특허 — 초고밀도 AS/RS
- **강점**: 검증된 고밀도 저장, 높은 처리량, 모듈 확장성
- **약점**: 개방형 환경 적용 불가, 사전 그리드 설치 필수, 폐쇄형 생태계

---


### 출처
- AutoStore(2026). *World's Fastest AS/RS*. https://www.autostoresystem.com/
- AutoStore(2022-12-13). *The Complete Guide to Warehouse Automation*. AutoStore. https://www.autostoresystem.com/insights/the-complete-guide-to-warehouse-automation
- AutoStore(2024-05-13). *AutoStore Brings World’s Fastest and Most Reliable Automated Storage and Retrieval System to CJ Logistics in Korea*. AutoStore. https://www.autostoresystem.com/news/autostore-brings-worlds-fastest-and-most-reliable-automated-storage-and-retrieval-system-to-cj-logistics-in-korea
- AutoStore(2023-08-18). *Warehouse Control Systems (WCS): Ultimate Guide*. AutoStore. https://www.autostoresystem.com/insights/warehouse-control-systems-wcs-ultimate-guide

## 7. Symbotic

### 하드웨어 스펙 (Symbot)
| 항목 | 스펙 |
|---|---|
| 이동 속도 | 약 40 km/h |
| 이동 방식 | 3D 격자 구조물 내 고속 이동 |
| 기능 | 케이스 피킹, AI 기반 팔레타이징 |

- **DoF**: 구조물 내 3DoF 고속 이동
- **센서**: 비전 카메라, 무선 통신 기반 위치 인식

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 4 (전용 구조물 내 완전 자율)
- **AI 알고리즘**: Store-friendly 팔레타이징 AI, 수백 대 실시간 최적화
- **핵심 기능**: 매장 진열 구조 맞춤 자동 적재 → 유통 효율 극대화
- **플랫폼**: 엔드투엔드 자율형 물류 플랫폼

### 기술 완성도
- **TRL**: 9 (Walmart 42개 유통센터 전면 도입, NASDAQ 상장)
- **HW+SW 통합도**: 매우 높음 (고속 로봇 + AI 팔레타이징 + 엔드투엔드 SW)
- **핵심 독창성**: AI 기반 Store-friendly 팔레타이징 — 유통 라스트마일 최적화
- **강점**: Walmart 대규모 레퍼런스, 수익성 검증, GreenBox WaaS 확장
- **약점**: 대형 유통업체 편중, 중소기업 도입 장벽 높음

---


### 출처
- Symbotic(2026). *Warehouse Automation for High Efficiency & Agility*. https://www.symbotic.com/

## 8. GreyOrange

### 하드웨어 스펙 (Ranger Series)
| 모델 | 기능 | Payload |
|---|---|---|
| Ranger RTP | Rack-to-Person GTP | 중형 선반 운반 |
| Ranger PickPal | 협동 피킹 AMR | 경량 |
| Ranger Forklift | 자율 지게차 | 팔레트급 중량 |
| Ranger XXL | 다중 트롤리 견인 | 대형 |

- **이동 방식**: 차동 구동, 전방향 이동
- **DoF**: 이동 3DoF
- **센서**: LiDAR, 카메라, IMU

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 3~4
- **AI 알고리즘**: 실시간 재고 우선순위 분석, 주문 흐름 최적화, ML 기반 경로 계획
- **플랫폼**: GreyMatter — 하드웨어 독립 오케스트레이션, 실시간 데이터 기반 의사결정

### 기술 완성도
- **TRL**: 8~9 (15,000대 이상 배포, H&M·Adidas·IKEA·Walmart 고객사)
- **HW+SW 통합도**: 높음 (개방형 HW + SW 중심 전략)
- **핵심 독창성**: 하드웨어 독립 개방형 오케스트레이션 — 멀티벤더 환경 강점
- **강점**: 대규모 배포 검증, 글로벌 리테일 레퍼런스, 유연한 통합성
- **약점**: 하드웨어 차별성 낮음, SW 중심 모델은 경쟁 심화

---


### 출처
- GreyOrange(2026). *GreyOrange 2026*. https://www.greyorange.com/
- GreyOrange(2026). *AI-Driven Orchestration and Inventory Management*. https://www.greyorange.com/home/
- GreyOrange(2026). *The GreyMatter Impact*. https://www.greyorange.com/greymatter/
- GreyOrange(2026). *Company*. https://www.greyorange.com/company/

## 9. RightHand Robotics

### 하드웨어 스펙 (RightPick 4)
| 항목 | 스펙 |
|---|---|
| 최대 Payload | 2 kg 이상 |
| 그리퍼 방식 | 하이브리드 (진공 흡입 + 핑거 결합) |
| 처리 속도 | 고속 낱개 피킹 (수백 picks/hour) |
| 이전 대비 개선 | 취급 크기 25% 증가, 무게 50% 향상 |

- **DoF**: 로봇 팔 6DoF + 그리퍼 복합
- **형태**: 고정형 피킹 스테이션

### 소프트웨어 및 AI
- **자율주행 레벨**: 해당 없음 (고정형)
- **AI 알고리즘**: Model-free AI 비전 피킹, 머신러닝 기반 SKU 인식, 컴퓨터 비전
- **핵심 기술**: 사전 학습 없이 수만 종 SKU 즉시 인식·파지 → 범용 피킹
- **플랫폼**: RightPick.AI + Fleet Management SW

### 기술 완성도
- **TRL**: 8~9 (Staples, Apotea 등 상용 운용, Rockwell Automation 전략 투자)
- **HW+SW 통합도**: 중간~높음 (자체 그리퍼 + AI SW 결합, HW 제조 역량 보유)
- **핵심 독창성**: Model-free 범용 피킹 AI + 하이브리드 그리퍼 — 다품종 소량에 최강
- **강점**: 다품종 SKU 처리 능력, Harvard 출신 기술 기반, Rockwell 파트너십
- **약점**: 고정형으로 이동성 없음, 피킹 단일 기능에 집중

---


### 출처
- RightHand Robotics(2026). *AI Powered Piece-Picking*. https://righthandrobotics.com/
- RightHand Robotics(2026). *About Us*. https://righthandrobotics.com/about-us
- RightHand Robotics(2026). *RightPick™ Piece-Picking Solutions*. https://righthandrobotics.com/products
- RightHand Robotics(2023). *Q1 Edition: Introducing our new CEO, Customer Video: Apotea, ProMat and LogiMat*. RightHand Robotics. https://righthandrobotics.com/jp/the-latest/q1-edition-introducing-our-new-ceo-customer-video-apotea-promat-and-logimat-built-ins-2023-best-places-to-work-award-and-news

## 10. Vecna Robotics

### 하드웨어 스펙
| 모델 | 기능 | 주요 스펙 |
|---|---|---|
| AFL (Autonomous Forklift) | 무인 지게차 | 최대 60인치(152 cm) 리프팅 |
| APT (Autonomous Pallet Truck) | 팔레트 장거리 운반 | 최대 3.6톤, 6.7 mph |
| ATG (Autonomous Tugger) | 대형 카트 견인 | 최대 4.5톤 견인 |
| CPJ (Co-bot Pallet Jack) | 협동 팔레트 잭 | 좁은 통로 대응 |

- **이동 방식**: 자율주행 (인프라 개조 없음)
- **DoF**: 이동 3DoF + 리프팅
- **센서**: LiDAR, 카메라, IMU

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 4 (통제 환경 완전 자율)
- **AI 알고리즘**: Pivotal AI 오케스트레이션, WMS 실시간 연동
- **플랫폼**: Pivotal™ + CaseFlow™ — 낱개 박스 피킹 2배 성능

### 기술 완성도
- **TRL**: 8~9 (FedEx, DHL, Caterpillar 실제 운용, 도입 1년 내 ROI 달성)
- **HW+SW 통합도**: 높음 (중대형 자율 지게차 전문화 + AI 오케스트레이션)
- **핵심 독창성**: 고중량 물류 특화 자율주행 — 3.6톤~4.5톤 무인 처리
- **강점**: 고하중 전문성, 입증된 ROI, 대형 물류사 레퍼런스
- **약점**: 대형 창고에 특화, 소규모 환경 적용성 낮음

---


### 출처
- Vecna Robotics(2026). *Vecna Robotics*. https://www.vecnarobotics.com/
- Vecna Robotics(2026). *About Us*. https://www.vecnarobotics.com/company/about-us/
- Vecna Robotics(2026). *Autonomous Mobile Robot (AMR) Technology*. https://www.vecnarobotics.com/the-vecna-system/vecna-autonomous-mobile-robots/

## 11. 6 River Systems

### 하드웨어 스펙 (Chuck / Chuck+)
| 항목 | 스펙 |
|---|---|
| Payload | 최대 90.7 kg (200 lbs) |
| 이동 방식 | 자율주행 AMR (인프라 불필요) |
| UI | 터치스크린 실시간 작업 지시 |
| 교육 시간 | 신입 작업자 15~30분 |

- **DoF**: 이동 3DoF
- **센서**: LiDAR, 카메라
- **특징**: 작업자 협동 피킹 (Co-bot 방식)

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 2~3 (작업자와 협동)
- **AI 알고리즘**: AI/ML 최적 경로 계산, 실시간 작업 배분
- **워크플로우**: 피킹·입고·재고실사·보충·분류 전 기능 지원
- **소속**: Ocado Group 산하 (2023년 인수)

### 기술 완성도
- **TRL**: 8~9 (DHL, Lockheed Martin, OfficeDepot 등 100개+ 현장)
- **HW+SW 통합도**: 중간 (경량 협동 AMR + AI SW, 완전 자율화 미달)
- **핵심 독창성**: 즉시 투입형(Plug & Play) 협동 AMR — 교육 최소화, 빠른 도입
- **강점**: 빠른 현장 적응, 낮은 도입 장벽, RaaS 모델
- **약점**: 완전 자율화 아님, Ocado 인수로 독자 전략 불투명

---


### 출처
- Ocado Intelligent Automation(2026). *OMRS: Ocado Mobile Robot System*. https://ocadointelligentautomation.com/systems/omrs-ocado-mobile-robot-system
- 6 River Systems(2023). *Contact Us*. https://info.ocado-ia.com/contact-general
- 6 River Systems(2024). *Meet Us At Manifest 2024*. https://info.6river.com/lp-manifest-2024

## 12. Floatic (플로틱)

### 하드웨어 스펙 (Flody)
| 항목 | 스펙 |
|---|---|
| 형태 | 협동 피킹 AMR |
| UI | 전면 스크린 작업 안내 |
| 도입 기간 | 약 6주 내 운영 |
| 성능 | 수작업 대비 피킹 생산성 최대 3.5배 |

- **이동 방식**: 자율주행 (인프라 불필요)
- **DoF**: 이동 3DoF

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 2~3
- **AI 알고리즘**: 군집 제어, 실시간 경로 최적화
- **플랫폼**: Floatic Engine — WMS 연동, 다중 로봇 충돌 방지 군집 제어

### 기술 완성도
- **TRL**: 7~8 (롯데글로벌로지스, 로지스올 상용화 단계)
- **HW+SW 통합도**: 중간 (협동 AMR + SW 플랫폼, 자체 설계 HW)
- **핵심 독창성**: 네이버랩스 출신 기술력 + K-물류 현장 최적화 빠른 도입
- **강점**: 국내 대형 물류사 레퍼런스, 빠른 도입(6주), 현대차 ZER01NE 투자
- **약점**: 해외 경쟁사 대비 규모 작음, 글로벌 진출 초기 단계

---


### 출처
- IFA NEXT Global Business Challenge(2023). *Floatic*. https://www.b2match.com/e/ifa-next-global-business-challenge/participations/274107
- WOWTALE(2024-06-12). *Floatic Secures KRW 5.2 Billion in Pre-Series A Bridge Investment*. https://en.wowtale.net/2024/06/12/78103/
- KoreaTechDesk(2024-06-16). *Floatic CEO Chan Lee on Leading Revolution in E-commerce Warehouse Automation with Visionary Strategy*. https://koreatechdesk.com/floatic-ceo-chan-lee-on-leading-revolution-in-e-commerce-warehouse-automation-with-visionary-strategy
- Korea Herald(2024-11-15). *Floatic and LogisALL Increase Warehouse Productivity By 3.5x*. https://www.koreaherald.com/article/3854963

## 13. Twinny (트위니)

### 하드웨어 스펙
| 모델 | 기능 | 주요 특징 |
|---|---|---|
| NarGo | 자율 이송 AMR | 인프라 없는 자율주행, 오더피킹 솔루션 |
| TarGo | 작업자 추종 로봇 | RGB-D + 딥러닝 대상 인식 |
| 더하고 | NarGo + TarGo 결합형 | 복합 기능 |

- **이동 방식**: 인프라 없는 자율주행 SLAM
- **DoF**: 이동 3DoF
- **센서**: RGB-D 카메라, LiDAR, IMU
- **특기**: 인건비 최대 60% 절감, 2025년 매출 전년 대비 3배 급증

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 3~4
- **AI 알고리즘**: 딥러닝 기반 사람 인식(TarGo), 실시간 SLAM, Physical AI 연구
- **플랫폼**: 군집 제어, 피지컬 AI 기반 산업용 로봇·휴머노이드 확장 중

### 기술 완성도
- **TRL**: 7~8 (코스닥 IPO 추진, 시리즈 C 204억 원, 누적 590억 원)
- **HW+SW 통합도**: 중간~높음 (KAIST 출신 기술, 자체 HW+SW+Physical AI)
- **핵심 독창성**: QR·비컨 없는 순수 AI 자율주행 + 딥러닝 사람 추종
- **강점**: 인프라 제로 전략, 높은 확장성, Physical AI 로드맵
- **약점**: 국내 중심, 글로벌 스케일업 초기

---


### 출처
- TWINNY(2026). *TWINNY*. https://twinny.ai/
- TWINNY(2026). *AMR*. https://twinny.ai/eng_amr
- TWINNY(2026). *Platform Outline*. https://twinny.ai/eng_platform
- WOWTALE(2026-03-17). *Autonomous Mobile Robot Firm TWINNY Completes $13.7M Series C Funding Round*. https://en.wowtale.net/2026/03/17/233680/
- K-Startup Center(2026). *Enterprise Together with KSC - TWINNY*. https://k-startupcenter.org/eng/CMS/IRContentMgr/view.do?mCode=MN015&seq=160

## 14. Thira Robotics (티라로보틱스)

### 하드웨어 스펙
| 시리즈 | 모델 | Payload | 특이사항 |
|---|---|---|---|
| T-Series | T200/300 | 200~300 kg | 표준 산업용 |
| T-Series | T600 | 600 kg | 중중량 |
| T-Series | T1000 | 1,000 kg | 10도 경사, 31mm 단차 극복 |
| L-Series | L200 | 200 kg | 초저상 (대차/롤테이너 하부 진입) |

- **이동 방식**: Hybrid SLAM 자율주행 (LiDAR + 비전)
- **DoF**: 이동 3DoF
- **특기**: 국내 최초 AMR 상용화 계보 (2013년~)

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 3~4
- **AI 알고리즘**: Hybrid SLAM (LiDAR + 비전 결합), 작업자 추종
- **플랫폼**: FMS(Fleet Management System) + 스마트 팩토리 솔루션 통합

### 기술 완성도
- **TRL**: 8~9 (삼성SDI, 아모레퍼시픽 대형 제조 현장 실증, 북미 수출)
- **HW+SW 통합도**: 높음 (ADM 구동부 100% 자체 설계 + Hybrid SLAM)
- **핵심 독창성**: 혹독한 산업 환경(오일, 경사, 단차) 특화 + 초저상 L-Series
- **강점**: 산업 현장 하드코어 적용 검증, LS티라유텍 모회사 지원
- **약점**: 시리즈 A 단계(225억 원 수준), 글로벌 인지도 초기

---


### 출처
- THIRA ROBOTICS(2026). *THIRA ROBOTICS*. https://www.thirarobotics.com/en
- THIRA ROBOTICS(2026). *Korean Site*. https://www.thirarobotics.com/
- THIRA ROBOTICS(2026). *Case Studies*. https://www.thirarobotics.com/en/amr/CaseStudies
- THIRA ROBOTICS(2026). *사례 연구*. https://www.thirarobotics.com/ko/amr/CaseStudies

## 15. Syscon (시스콘로보틱스)

### 하드웨어 스펙
| 시리즈 | 모델 | Payload |
|---|---|---|
| SR (Smart Robot) | SR1~SR7 | 80 kg ~ 1,000 kg |
| HP (Heavy Payload) | - | 5,000 kg 이상 |
| DLF/LGV | 무인 지게차 | 팔레트급 |
| IM (서비스) | IM5 등 | 안내/배송 |

- **이동 방식**: AGV+AMR 하이브리드
- **DoF**: 이동 3DoF + 차상 모듈 교체형 (컨베이어, 리프트, 협동 로봇)
- **센서**: LiDAR, 카메라, IMU

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 3~4
- **AI 알고리즘**: 자율주행, 군집 제어
- **플랫폼**: 최상위 제어 SW 자체 개발, WMS 연동

### 기술 완성도
- **TRL**: 8~9 (현대차·현대위아·삼성전자·LG전자 수백 대 실전 배치, 북미 EV/배터리 수출)
- **HW+SW 통합도**: 높음 (80kg~5톤 전 라인업 자체 제작 + 제어 SW 수직 계열화)
- **핵심 독창성**: 80kg~5톤 초광폭 페이로드 범위 + 모듈 교체형 차상부
- **강점**: 국내 대기업 대규모 레퍼런스, 10년+ 공장 자동화 경험, 브이원텍 모회사
- **약점**: 소프트웨어 AI 역량 해외 대비 약함, 브랜드 글로벌 인지도 낮음

---


### 출처
- 시스콘로보틱스(2026). *시스콘_자율주행 로봇*. https://sysconrobotics.com/
- 시스콘로보틱스(2026). *회사 소개*. https://sysconrobotics.com/company_1.html
- 시스콘로보틱스(2026). *제품 문의*. https://sysconrobotics.com/contact.html
- Digital Today(2026-01-23). *Syscon Robotics container unmanned transport technology designated as new logistics technology*. https://www.digitaltoday.co.kr/en/view/1905/syscon-robotics-container-unmanned-transport-technology-designated-as-new-logistics-technology

## 16. Clobot (클로봇)

### 하드웨어 스펙
- **하드웨어 직접 제조 없음** — 범용 SW 플랫폼 + 파트너 HW
- **파트너**: Boston Dynamics Spot, 레인보우로보틱스 등

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 3~4 (탑재 대상 로봇 의존)
- **AI 알고리즘**: 범용 자율주행 SW(CHAMELEON), 이기종 로봇 통합 제어
- **플랫폼**:
  - **CHAMELEON**: 어떤 HW에도 탑재 가능한 범용 자율주행 SW
  - **CROMS**: 이기종 로봇 통합 관제 (서로 다른 제조사 로봇 단일 시스템 제어)

### 기술 완성도
- **TRL**: 8~9 (코스닥 상장 완료 2024년 10월, 기업 가치 ~1.3조 원)
- **HW+SW 통합도**: 낮음(HW 없음) → 이기종 통합 SW는 국내 최고 수준
- **핵심 독창성**: HW 독립 범용 자율주행 + 이기종 로봇 통합 관제 — 국내 1호
- **강점**: 현대차·롯데·신세계 130개+ 고객사, 코스닥 상장, 네이버/현대차 투자
- **약점**: HW 부재로 솔루션 완결성 낮음, 해외 경쟁사(Covariant 등) 대비 AI 깊이

---

## 17. Bigwave Robotics (빅웨이브로보틱스)

### 하드웨어 스펙
- **하드웨어 직접 제조 없음** — 로봇 자동화 플랫폼/매칭 서비스

### 소프트웨어 및 AI
- **자율주행 레벨**: 해당 없음 (플랫폼/매칭 사업)
- **AI 알고리즘**: AI 기반 로봇 자동화 매칭(2만 건+ DB), AI 오케스트레이션
- **플랫폼**:
  - **마로솔(Marosol)**: 국내 1위 로봇 자동화 매칭 플랫폼 (500개+ 공급사)
  - **솔링크(SOLlink)**: 이기종 로봇 통합 관제 + 건물 인프라(엘리베이터·자동문) 연동
  - **RaaS 금융**: 로봇 전용 리스·렌탈·보험·중고 마켓

### 기술 완성도
- **TRL**: 7~8 (코스닥 예비심사 2025년 12월 제출, 국가 로봇 테스트필드 주관)
- **HW+SW 통합도**: 낮음(HW 없음) → 플랫폼 생태계 구축 강점
- **핵심 독창성**: 로봇 도입 전 과정(정보-구매-운영-관리) 수직 계열화 플랫폼
- **강점**: 로봇 생태계 플랫폼 선점, RaaS 금융 혁신, 수익성 동반 성장
- **약점**: 로봇 핵심 기술 부재, 플랫폼 종속성 리스크

---

## 18. Seoul Robotics (서울로보틱스)

### 하드웨어 스펙
- **하드웨어 직접 제조 없음** — 인프라 설치형 센서+SW 솔루션
- **센서**: LiDAR (외부 설치형), 카메라

### 소프트웨어 및 AI
- **자율주행 레벨**: Level 4~5 (ATI: 인프라 측이 자율화, 차량 자체는 일반 차량)
- **핵심 AI**: SENSR™ — 딥러닝 기반 악천후 3D 인지 (눈·비 등)
- **AI 알고리즘**: 3D 비전 딥러닝, 다객체 추적, 자율 경로 제어
- **플랫폼**:
  - **LV5 CTRL TWR**: 인프라 측에서 비자율 차량 원격 제어 (수백 대 동시)
  - **SENSR™**: 세계 최고 수준 악천후 3D 인지 SW
  - **Discovery**: HW+SW 올인원 솔루션

### 기술 완성도
- **TRL**: 7~8 (BMW 딩골핑 공장 실제 적용, 닛산 공장 물류 수주)
- **HW+SW 통합도**: 중간 (인프라 HW + SENSR SW, 차량 HW 불필요)
- **핵심 독창성**: ATI(Autonomy Through Infrastructure) 세계 최초 상용화 — 차량 개조 없이 자율화
- **강점**: BMW·닛산 글로벌 OEM 레퍼런스, 독창적 역발상 기술, 악천후 강인성
- **약점**: 매출 규모 아직 작음(42억 원), IPO 자진 철회, 제한적 적용 환경

---

## 기술 지표 요약표

| 스타트업 | TRL | Payload 범위 | 자율주행 레벨 | HW+SW 통합 | 핵심 AI 기술 |
|---|---|---|---|---|---|
| Locus Robotics | 8~9 | 36~1,360 kg | L2~3 | 중간 | 경로 최적화, 군집 제어 |
| Exotec | 8~9 | 토트급 | L4 | 높음 | AI 비전 피킹, 3D 경로 |
| Geek+ | 9 | 500~3,000 kg | L4 | 매우 높음 | RL 스케줄링, CV 피킹 |
| Covariant | 7~8 | ~2 kg | 해당없음 | 낮음(SW) | RFM-1, Model-free 피킹 |
| Agility Robotics | 7~8 | ~16 kg | L3~4 | 높음 | RL 보행, CV 물체인식 |
| AutoStore | 9 | 빈 단위 | L4 | 높음 | 경로 최적화, 빈 재배치 |
| Symbotic | 9 | 케이스급 | L4 | 매우 높음 | AI 팔레타이징, 고속제어 |
| GreyOrange | 8~9 | 중~대형 | L3~4 | 높음 | 실시간 재고 AI, 경로 ML |
| RightHand | 8~9 | ~2 kg | 해당없음 | 중~높음 | Model-free CV, 하이브리드 그리퍼 |
| Vecna Robotics | 8~9 | 3,600~4,500 kg | L4 | 높음 | AI 오케스트레이션 |
| 6 River Systems | 8~9 | ~90 kg | L2~3 | 중간 | AI 경로 최적화 |
| Floatic | 7~8 | 경량 | L2~3 | 중간 | 군집 제어, 경로 최적화 |
| Twinny | 7~8 | 중형 | L3~4 | 중~높음 | 딥러닝 추종, Physical AI |
| Thira Robotics | 8~9 | 200~1,000 kg | L3~4 | 높음 | Hybrid SLAM |
| Syscon | 8~9 | 80~5,000 kg | L3~4 | 높음 | 자율주행, 군집 제어 |
| Clobot | 8~9 | HW 없음 | L3~4(탑재 의존) | 낮음(SW) | 범용 자율주행, 이기종 관제 |
| Bigwave | 7~8 | HW 없음 | 해당없음 | 낮음(플랫폼) | AI 매칭, 오케스트레이션 |
| Seoul Robotics | 7~8 | HW 없음 | L4~5(ATI) | 중간 | 딥러닝 3D 인지, 원격제어 |