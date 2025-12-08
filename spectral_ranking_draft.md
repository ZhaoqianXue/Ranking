OmniRank: A Large-Language-Model Agent Platform for Statistically Rigorous Ranking Inference from Arbitrary Multiway Comparisons

Target: Nature Communications

ABSTRACT
Spectral ranking inferences provide a minimax optimal solution for analyzing multiway comparison data, which could achieve the same asymptotic efficiency as the Maximum Likelihood Estimation (MLE) while providing extra uncertainty quantifications. However, the steep learning curve of linear algebra-based implementations restricts their utility to a small circle of statisticians. In this study, we present OmniRank, an agentic framework that synergizes reasoning capabilities of Large Language Models (LLMs) with the mathematical rigor of spectral ranking inference. Unlike standard LLMs that are prone to hallucinations in arithmetic tasks, OmniRank decouples instruction following from computation: an LLM controller parses user queries and data, delegating the rigorous inference to a specialized Spectral Calculation Engine. Case study results on both synthetic and real-world datasets confirm that OmniRank achieves precise ranking recovery matching established statistical packages. By providing an interactive, no-code interface for spectral ranking, OmniRank democratizes advanced ranking methods and uncertainty inference for domain experts across social and natural sciences.

1. Introduction
Ranking inferences from comparison data are ubiquitous in scientific inquiry and modern applications, ranging from identifying optimal treatments in clinical trials and ranking biological stimuli to evaluating the relative strength of competitors in sports and gaming1,2. While classical frameworks like the Bradley-Terry-Luce model have successfully handled pairwise comparisons, real-world data increasingly manifest as multiway comparisons, where multiple items are compared simultaneously—such as in horse races, multi-player online games, or top- choice data in econometrics3,4. Unlike pairwise data, multiway comparisons involve hyperedges of heterogeneous sizes, creating complex dependency structures that defy simple aggregation. Although the Plackett-Luce model offers a probabilistic foundation for such data, its reliance on Maximum Likelihood Estimation (MLE) faces significant challenges: the likelihood function can be non-convex, and the computational burden becomes prohibitive as the number of items (n) grows, often requiring o(N3) complexity for precise inference5,6.

To overcome these computational and statistical barriers, recent theoretical breakthroughs have established spectral ranking inferences based on general multiway comparisons as a superior alternative. By constructing a comparison graph where items are nodes and multiway comparisons form hyperedges, these methods utilize the stationary distribution of a random walk on the hypergraph (or the eigenvectors of the hypergraph Laplacian) to recover latent preference scores7. Fan et al. demonstrated that this spectral approach achieves minimax optimal statistical rates comparable to MLE but with significantly greater computational efficiency, even under heterogeneous sampling conditions where hyperedge sizes vary dramatically8. Despite this theoretical elegance, the practical application of spectral ranking remains confined to a small circle of statisticians. The implementation requires rigorous handling of sparse hypergraph adjacency matrices and complex linear algebra operations, creating a steep technical barrier for domain experts—such as sociologists or biologists—who possess rich multiway data but lack the coding expertise to implement these specialized spectral algorithms9.

Large Language Models (LLMs) have emerged as potential intermediaries to democratize such advanced analytical tools. Models like GPT-4 have shown impressive capabilities in code generation and logical reasoning10, 11. However, standard LLMs inherently struggle with rigorous mathematical execution; they are prone to "hallucinations" when performing arithmetic or executing specific algorithms mentally, and they lack the native ability to process large-scale structured data (e.g., adjacency matrices) directly within their context window12. Consequently, the current wave of "AI Agents" has shifted towards a tool-use paradigm, where the LLM acts as a controller that delegates specific tasks to external computational tools13, 14. While agents have been developed for chemical synthesis15 and gene analysis16, there is currently no dedicated framework that bridges the gap between the sophisticated mathematics of spectral ranking and the intuitive needs of non-technical users.

Here, we introduce OmniRank, a novel web-based agentic framework that democratizes access to spectral ranking inferences. The architecture consists of two synergistic components: an LLM Agent that interprets user’s natural language requests and raw data uploads (e.g., “Rank these polygenic risk scores for breast cancer using their comparative AUC performance across the uploaded validation cohorts.”), and a Spectral Calculation Engine that executes the hypergraph construction and eigenvector computations. The results are then rendered through an interactive visualization dashboard, allowing users to explore ranking confidence intervals and topology without writing a single line of code. By decoupling the complex spectral inference (Backend) from the user interaction (Frontend), we ensure that the mathematical precision of the underlying theory is preserved while maximizing accessibility.

We validated the efficacy of OmniRank through both theoretical benchmarking and real-world application scenarios. To assess the fidelity of our agent-driven pipeline, we compared its output against standard R implementations of spectral ranking on synthetic datasets with varying heterogeneity in comparison sizes (). Furthermore, we demonstrate the tool’s practical utility by applying it to a real-world LLMs dataset, where the agent successfully parsed unstructured match results and produced rankings consistent with ground-truth outcomes. Our results show that by combining the reasoning power of LLMs with the mathematical rigor of spectral graph theory, we can effectively lower the barrier to entry for advanced statistical ranking, enabling broader application across diverse scientific fields.

2. Methods
2.1 Overview of the OmniRank Framework Architecture 
Objective: To provide a high-level overview of the system's operation. Describe the interaction flow between the LLM Agent, the Spectral Ranking Engine, and the Visualization Dashboard.
Content: Define the system's Input (Natural Language + Raw Data), Intermediate Processing (Agent Parsing & Tool Invocation), and Output (Visualized Ranking).
2.2 Spectral Ranking Inference Engine Implementation
In general, the spectral ranking approach transforms pairwise comparison data into a Markov chain over the n items and leverages its stationary distribution to infer item scores. We assume there are n items to be ranked, and the preference scores of a given group of n items can be parameterized as a  o(*1, ..., *n )Tsuch that for any choice set A and item iA we have 
P(i wins among A)=e*i/kAe*k 
For a general comparison model of the n items, we are given a collection of  comparisons and outcomes  {(cl, Al)}lD where cl denotes the selected item over the choice set Al. Specifically, we construct a directed comparison graph where each item corresponds to a state, and define a transition matrix P with transition probability whose entries encode empirical comparison outcomes, which is defined as
Pij =1dlWjLi1f(Ai) 
Where Wj and  Li is defined as two index sets for comparisons, with j as the winner and i as the loser and their intersection for ij gives all situations where i, j are compared and j wins, i.e., WjLi={lD|i, jAl, cl= j}. This matrix characterizes a Markov chain whose long-term visiting frequency reflects the underlying preference structure. The stationary distribution π of this chain—obtained as the leading eigenvector of PT associated with eigenvalue 1—serves as the spectral score for each item. Compared to likelihood-based models such as Bradley–Terry–Luce (BTL) or Plackett–Luce (PL), which require iterative optimization, spectral methods are computationally simpler: only a single eigen-decomposition is needed, i.e., O(n3) complexity, making them scalable and robust in large, sparse comparison graphs. To align with latent-utility models, the spectral scores can be further transformed into estimated preference parameters via
i=logi-1nk=1nlogk 
Finally, the inferred ranking is produced by sorting i in descending order. Furthermore, we use the following estimation of  π to inference uncertainty quantification
i=jiPjiπjjiPji 
In summary, spectral ranking offers a principled, computationally efficient alternative to likelihood-based ranking methods by exploiting the spectral properties of a Markov transition matrix constructed from pairwise comparisons. For more information, we refer to this method article17.

Objective: Theoretical implementation of the project. Detailed description on how to translate the theory of Spectral Ranking Inferences into code.
Content:
Hypergraph Construction: Describe how the hypergraph is constructed from Multiway Comparison data.
Laplacian & Eigenvector Computation: Detail the specific mathematical computation steps (e.g., constructing the Random Walk Transition Matrix, solving for the Stationary Distribution/Eigenvector). Highlight the optimization of the O(n3) complexity or the specific use of linear algebra libraries.
Note: Describe the "computational process?"

2.3 LLM Agent Design and Tool Integration
Objective: To describe the implementation details of the AI component.
Content:
Model Selection: Specify the model used (e.g., GPT-5-nano) and the temperature setting.
Prompt Engineering: Describe the design strategy for the System Prompt, focusing on how the LLM is instructed to understand the structure of multiway comparison data.
Function Calling / Tool Use: Describe how the Agent invokes the backend Spectral Ranking Engine via an API, rather than attempting the calculation itself (to prevent hallucination).

3. Case Studies
3.1 Chatbots Arena Leaderboard
Objective: Validate the system's practical application value.
Content:
Describe the data source (e.g., Chatbot Arena or similar anonymous battle data).
Describe the Data Preprocessing steps: how unstructured battle logs are transformed into the model-readable Multiway comparison format.
3.2 Ensemble Polygenic Risk Score Model 

3.3 General Benchmarking, Evaluation Metrics and Statistical Analysis
Describe the Baselines for comparison: e.g., Bradley-Terry (Pairwise), Maximum Likelihood Estimation (MLE) methods, etc.
Ranking Accuracy/Error Metrics?
Agent Performance: Describe how to evaluate the Agent's accuracy in understanding user instructions (e.g., parsing correctness rate).

4. Conclusion and Discussion

References:
1. Cattelan, M. Models for paired comparison data: A review with applications to sports. Statistical Modelling 12, 319–343 (2012). https://arxiv.org/abs/1210.1016 

2. Luce, R. D. Individual Choice Behavior: A Theoretical Analysis. (Wiley, 1959). https://psycnet.apa.org/record/1960-03588-000 

3. Guiver, J. & Snelson, E. Bayesian inference for Plackett-Luce ranking models. in Proceedings of the 26th International Conference on Machine Learning (ICML) 377–384 (2009). https://icml.cc/Conferences/2009/papers/347.pdf 

4. Hunter, D. R. MM algorithms for generalized Bradley-Terry models. The Annals of Statistics 32, 384–406 (2004). https://projecteuclid.org/journals/annals-of-statistics/volume-32/issue-1/MM-algorithms-for-generalized-Bradley-Terry-models/10.1214/aos/1079120141.full 

5. Maystre, L. & Grossglauser, M. Fast and accurate inference of Plackett-Luce models. in Advances in Neural Information Processing Systems (NeurIPS) 28 (2015). https://proceedings.neurips.cc/paper_files/paper/2015/hash/2a38a4a9316c49e5a833517c45d31070-Abstract.html 

6. Hajek, B., Oh, S. & Xu, J. Minimax-optimal inference from partial rankings. in Advances in Neural Information Processing Systems (NeurIPS) 27 (2014). https://proceedings.neurips.cc/paper_files/paper/2014/hash/daadbd06d5082478b7677bea9812b575-Abstract.html 

7. Negahban, S., Oh, S. & Shah, D. Iterative ranking from pair-wise comparisons. in Advances in Neural Information Processing Systems (NeurIPS) 25 (2012). https://papers.nips.cc/paper/4701-iterative-ranking-from-pair-wise-comparisons 

8. Fan, J. et al. Spectral Ranking Inferences based on General Multiway Comparisons. arXiv preprint arXiv:2308.02918 (2023). https://arxiv.org/abs/2308.02918 

9. Davenport, T. & Kalakota, R. The potential for artificial intelligence in healthcare. Future Healthcare Journal 6, 94–98 (2019). https://pmc.ncbi.nlm.nih.gov/articles/PMC6616181/ 

10. Xu, Z. et al. Toward large reasoning models: A survey of reinforced reasoning in large language models. Patterns 6, 100983 (2025). https://www.sciencedirect.com/science/article/pii/S2666389925002181 

11. Binz, M. & Schulz, E. Large language models could change the future of behavioral science. Nat. Rev. Psychol. 3, 284–296 (2024). https://www.nature.com/articles/s44159-024-00307-x 

12. Dziri, N. et al. Faith and Fate: Limits of Transformers on Compositionality. in Advances in Neural Information Processing Systems (NeurIPS) 36 (2023). https://arxiv.org/abs/2305.18654 

13. Schick, T. et al. Toolformer: Language Models Can Teach Themselves to Use Tools. in Advances in Neural Information Processing Systems (NeurIPS) 36 (2023). https://arxiv.org/abs/2302.04761 

14. Liang, Y. et al. TaskMatrix.AI: Completing Tasks by Connecting Foundation Models with Millions of APIs. Intelligent Computing 3, 0063 (2024). https://spj.science.org/doi/10.34133/icomputing.0063 

15. Bran, A. M. et al. ChemCrow: Augmenting large-language models with chemistry tools. Nature Machine Intelligence 6, 525–537 (2024). https://www.nature.com/articles/s42256-024-00832-8 

16. Hu, Z. et al. GeneAgent: self-verification language agent for gene-set analysis using domain databases. Nat. Methods 22, 1677–1685 (2025). https://www.nature.com/articles/s41592-025-02748-6 

17. Fan, Jianqing, Zhipeng Lou, Weichen Wang, and Mengxin Yu. "Spectral ranking inferences based on general multiway comparisons." Operations Research (2025). https://doi.org/10.1287/opre.2023.0439