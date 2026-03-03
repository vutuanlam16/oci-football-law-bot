"""
Chatbot Evaluation Script
Đánh giá độ chính xác của RAG chatbot luật bóng đá
"""

import json
import requests
import time
from typing import Dict, List, Tuple
from datetime import datetime
import numpy as np
from collections import defaultdict


class ChatbotEvaluator:
    """Đánh giá chatbot qua nhiều metrics khác nhau"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.results = []
        
    def load_test_dataset(self, filepath: str) -> Dict:
        """Load test dataset từ JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def query_chatbot(self, question: str) -> Tuple[str, List[str], float]:
        """
        Gửi câu hỏi đến chatbot API
        Returns: (answer, sources, response_time)
        """
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.api_base_url}/chat",
                json={"message": question},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            response_time = time.time() - start_time
            answer = data.get("answer", "")
            sources = data.get("sources", [])
            
            return answer, sources, response_time
            
        except Exception as e:
            print(f"❌ Error querying chatbot: {e}")
            return "", [], time.time() - start_time
    
    def evaluate_keyword_match(self, answer: str, expected_keywords: List[str]) -> float:
        """
        Đánh giá dựa trên keyword matching
        Returns: Score 0.0-1.0
        """
        if not expected_keywords:
            return 1.0
        
        answer_lower = answer.lower()
        matched = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
        
        return matched / len(expected_keywords)
    
    def evaluate_semantic_similarity(self, answer: str, expected_answer: str) -> float:
        """
        Đánh giá dựa trên semantic similarity
        Sử dụng Ollama embeddings nếu có
        Returns: Score 0.0-1.0
        """
        try:
            # Get embeddings cho cả 2 câu
            answer_emb = self._get_embedding(answer)
            expected_emb = self._get_embedding(expected_answer)
            
            if answer_emb is None or expected_emb is None:
                return 0.0
            
            # Cosine similarity
            similarity = np.dot(answer_emb, expected_emb) / (
                np.linalg.norm(answer_emb) * np.linalg.norm(expected_emb)
            )
            
            return float(similarity)
            
        except Exception as e:
            print(f"⚠️  Semantic similarity error: {e}")
            return 0.0
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding vector từ Ollama"""
        try:
            response = requests.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "prompt": text
                },
                timeout=10
            )
            response.raise_for_status()
            embedding = response.json().get("embedding", [])
            return np.array(embedding) if embedding else None
            
        except Exception:
            return None
    
    def evaluate_answer_presence(self, answer: str) -> bool:
        """Kiểm tra chatbot có trả lời không"""
        return len(answer.strip()) > 0
    
    def evaluate_source_presence(self, sources: List[str]) -> bool:
        """Kiểm tra có trích dẫn nguồn không"""
        return len(sources) > 0
    
    def evaluate_single_question(self, test_case: Dict) -> Dict:
        """
        Đánh giá một câu hỏi
        Returns: Dict với các metrics
        """
        question = test_case["question"]
        expected_answer = test_case["expected_answer"]
        expected_keywords = test_case["keywords"]
        
        print(f"\n🔍 Câu hỏi: {question}")
        
        # Query chatbot
        answer, sources, response_time = self.query_chatbot(question)
        
        print(f"💬 Trả lời: {answer[:100]}..." if len(answer) > 100 else f"💬 Trả lời: {answer}")
        
        # Evaluate metrics
        has_answer = self.evaluate_answer_presence(answer)
        has_sources = self.evaluate_source_presence(sources)
        keyword_score = self.evaluate_keyword_match(answer, expected_keywords)
        semantic_score = self.evaluate_semantic_similarity(answer, expected_answer)
        
        # Combined accuracy score (weighted average)
        accuracy_score = (
            0.4 * keyword_score +      # 40% keyword matching
            0.5 * semantic_score +      # 50% semantic similarity  
            0.1 * (1.0 if has_sources else 0.0)  # 10% có nguồn trích dẫn
        )
        
        result = {
            "test_id": test_case["id"],
            "category": test_case["category"],
            "question": question,
            "expected_answer": expected_answer,
            "actual_answer": answer,
            "sources": sources,
            "response_time": response_time,
            "has_answer": has_answer,
            "has_sources": has_sources,
            "keyword_score": keyword_score,
            "semantic_score": semantic_score,
            "accuracy_score": accuracy_score,
            "matched_keywords": sum(1 for kw in expected_keywords if kw.lower() in answer.lower()),
            "total_keywords": len(expected_keywords)
        }
        
        print(f"📊 Scores: Keyword={keyword_score:.2f}, Semantic={semantic_score:.2f}, Overall={accuracy_score:.2f}")
        
        return result
    
    def run_evaluation(self, dataset_path: str) -> Dict:
        """
        Chạy evaluation trên toàn bộ dataset
        Returns: Dict với overall metrics
        """
        print("=" * 80)
        print("🚀 BẮT ĐẦU ĐÁNH GIÁ CHATBOT")
        print("=" * 80)
        
        # Load dataset
        dataset = self.load_test_dataset(dataset_path)
        test_cases = dataset["test_cases"]
        
        print(f"\n📋 Tổng số câu hỏi: {len(test_cases)}")
        print(f"📂 Danh mục: {list(dataset['metadata']['categories'].keys())}")
        
        # Evaluate từng câu hỏi
        self.results = []
        for test_case in test_cases:
            result = self.evaluate_single_question(test_case)
            self.results.append(result)
            time.sleep(0.5)  # Tránh overload API
        
        # Calculate overall metrics
        overall_metrics = self.calculate_overall_metrics()
        
        return overall_metrics
    
    def calculate_overall_metrics(self) -> Dict:
        """Tính toán overall metrics từ results"""
        if not self.results:
            return {}
        
        # Overall scores
        total_questions = len(self.results)
        answered_questions = sum(1 for r in self.results if r["has_answer"])
        questions_with_sources = sum(1 for r in self.results if r["has_sources"])
        
        avg_keyword_score = np.mean([r["keyword_score"] for r in self.results])
        avg_semantic_score = np.mean([r["semantic_score"] for r in self.results])
        avg_accuracy_score = np.mean([r["accuracy_score"] for r in self.results])
        avg_response_time = np.mean([r["response_time"] for r in self.results])
        
        # Per-category metrics
        category_metrics = defaultdict(list)
        for r in self.results:
            category_metrics[r["category"]].append(r["accuracy_score"])
        
        category_scores = {
            cat: np.mean(scores) for cat, scores in category_metrics.items()
        }
        
        # Thống kê keywords
        total_keywords = sum(r["total_keywords"] for r in self.results)
        matched_keywords = sum(r["matched_keywords"] for r in self.results)
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "total_questions": total_questions,
            "answered_questions": answered_questions,
            "answer_rate": answered_questions / total_questions,
            "questions_with_sources": questions_with_sources,
            "source_rate": questions_with_sources / total_questions,
            "avg_keyword_score": float(avg_keyword_score),
            "avg_semantic_score": float(avg_semantic_score),
            "avg_accuracy_score": float(avg_accuracy_score),
            "avg_response_time": float(avg_response_time),
            "keyword_match_rate": matched_keywords / total_keywords if total_keywords > 0 else 0,
            "category_scores": category_scores,
            "detailed_results": self.results
        }
        
        return metrics
    
    def generate_report(self, metrics: Dict, output_path: str):
        """Tạo báo cáo JSON chi tiết"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Báo cáo đã lưu: {output_path}")
    
    def print_summary(self, metrics: Dict):
        """In ra tóm tắt kết quả"""
        print("\n" + "=" * 80)
        print("📊 KẾT QUẢ ĐÁNH GIÁ CHATBOT")
        print("=" * 80)
        
        print(f"\n📈 OVERALL METRICS:")
        print(f"  • Tổng câu hỏi: {metrics['total_questions']}")
        print(f"  • Trả lời được: {metrics['answered_questions']}/{metrics['total_questions']} ({metrics['answer_rate']*100:.1f}%)")
        print(f"  • Có trích dẫn nguồn: {metrics['questions_with_sources']}/{metrics['total_questions']} ({metrics['source_rate']*100:.1f}%)")
        
        print(f"\n🎯 ACCURACY SCORES:")
        print(f"  • Overall Accuracy: {metrics['avg_accuracy_score']*100:.1f}%")
        print(f"  • Keyword Match: {metrics['avg_keyword_score']*100:.1f}%")
        print(f"  • Semantic Similarity: {metrics['avg_semantic_score']*100:.1f}%")
        print(f"  • Keyword Coverage: {metrics['keyword_match_rate']*100:.1f}%")
        
        print(f"\n⚡ PERFORMANCE:")
        print(f"  • Avg Response Time: {metrics['avg_response_time']:.2f}s")
        
        print(f"\n📂 SCORES BY CATEGORY:")
        for category, score in sorted(metrics['category_scores'].items(), key=lambda x: x[1], reverse=True):
            print(f"  • {category:20s}: {score*100:.1f}%")
        
        # Top 5 best questions
        print(f"\n✅ TOP 5 CÂU TRẢ LỜI TỐT NHẤT:")
        sorted_results = sorted(
            metrics['detailed_results'],
            key=lambda x: x['accuracy_score'],
            reverse=True
        )
        for i, r in enumerate(sorted_results[:5], 1):
            print(f"  {i}. [{r['accuracy_score']*100:.0f}%] {r['question']}")
        
        # Top 5 worst questions
        print(f"\n❌ TOP 5 CÂU TRẢ LỜI YẾU NHẤT:")
        for i, r in enumerate(sorted_results[-5:][::-1], 1):
            print(f"  {i}. [{r['accuracy_score']*100:.0f}%] {r['question']}")
        
        print("\n" + "=" * 80)


def main():
    """Main evaluation function"""
    evaluator = ChatbotEvaluator(api_base_url="http://localhost:8000")
    
    # Run evaluation
    metrics = evaluator.run_evaluation("evaluation/test_dataset.json")
    
    # Print summary
    evaluator.print_summary(metrics)
    
    # Save detailed report
    evaluator.generate_report(
        metrics,
        f"evaluation/evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    
    # Return overall accuracy for scripting
    return metrics['avg_accuracy_score']


if __name__ == "__main__":
    accuracy = main()
    print(f"\n🎯 Final Accuracy: {accuracy*100:.1f}%")
