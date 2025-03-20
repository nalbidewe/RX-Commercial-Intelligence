import { useState, useEffect } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function MultiSelectQuestions() {
  // Use the globally injected `props` object.
  const initialQuestions = props.questions || [];
  
  // Track visible questions and their hierarchy
  const [visibleQuestions, setVisibleQuestions] = useState([]);
  
  // Initialize visible questions with the top-level questions
  useEffect(() => {
    setVisibleQuestions(initialQuestions.map(q => ({
      ...q,
      level: 0,
      parentId: null,
      parentValue: null
    })));
  }, []);

  // Determine which action to call based on tool type
  // Check if any questions exist and look for toolType property on the first question
  // Determine which tool type we're working with
  const toolType = initialQuestions.length > 0 ? 
    initialQuestions[0].toolType : null;
  
  // Set the action name based on the tool type
  const submitActionName = (() => {
    switch(toolType) {
      case "lifecycle":
        return "submit_lifecycle_selections";
      case "social_media":
        return "submit_social_media_selections";
      case "web_app":
      default:
        return "submit_selections";
    }
  })();
  
  // Flag to determine if we're using the lifecycle form logic
  const isLifecycleForm = toolType === "lifecycle";
  const isSocialMediaForm = toolType === "social_media";

  // Update selections and dynamically adjust visible questions
  const handleSelectChange = (questionId, value) => {
    // First, find the question that was answered
    const questionIndex = visibleQuestions.findIndex(q => q.questionId === questionId);
    if (questionIndex === -1) return;

    // Create a copy of the current questions
    const updatedQuestions = [...visibleQuestions];
    
    // Handle special cases: "Other" or "Yes, add additional info"
    if (value === "Other (Enter your own)" || value === "Yes, add additional info") {
      updatedQuestions[questionIndex] = {
        ...updatedQuestions[questionIndex],
        isOther: true,
        selected: ""
      };
    } else {
      updatedQuestions[questionIndex] = {
        ...updatedQuestions[questionIndex],
        isOther: false,
        selected: value
      };
    }
    
    // For lifecycle form, handle sub-questions
    if (isLifecycleForm || isSocialMediaForm) {
      // Find the current question
      const currentQuestion = initialQuestions.find(q => q.questionId === questionId);
      
      // Also search in any subQuestions that might be present in visible questions
      let foundSubQuestion;
      if (!currentQuestion) {
        for (const question of visibleQuestions) {
          if (question.subQuestions && question.subQuestions[question.selected]) {
            const subQs = question.subQuestions[question.selected];
            foundSubQuestion = subQs.find(sq => sq.abbrev === questionId);
            if (foundSubQuestion) break;
          }
        }
      }
      
      const targetQuestion = currentQuestion || foundSubQuestion;
      
      // Remove any existing sub-questions that depended on the previous answer
      const level = updatedQuestions[questionIndex].level || 0;
      const questionToRemoveIds = new Set();
      
      // Find all child questions to remove (and their children)
      const findChildrenToRemove = (parentId, startIdx = 0) => {
        for (let i = startIdx; i < updatedQuestions.length; i++) {
          const q = updatedQuestions[i];
          if (q.parentId === parentId) {
            questionToRemoveIds.add(q.questionId);
            // Recursively find children of this question too
            findChildrenToRemove(q.questionId, i + 1);
          }
        }
      };
      
      findChildrenToRemove(questionId, questionIndex + 1);
      
      // Filter out questions that need to be removed
      const filteredQuestions = updatedQuestions.filter(q => !questionToRemoveIds.has(q.questionId));
      
      // Add new sub-questions if this answer has any
      if (targetQuestion && targetQuestion.subQuestions && targetQuestion.subQuestions[value]) {
        const subQuestions = targetQuestion.subQuestions[value].map(sq => ({
          questionId: sq.abbrev,
          question: sq.question,
          type: sq.type || "options",
          options: sq.value || [],
          selected: "",
          isOther: false,
          subQuestions: sq.sub_questions || {},
          level: level + 1,
          parentId: questionId,
          parentValue: value
        }));
        
        // Insert sub-questions right after their parent question
        filteredQuestions.splice(questionIndex + 1, 0, ...subQuestions);
      }
      
      setVisibleQuestions(filteredQuestions);
    } else {
      // For non-lifecycle forms, just update the question
      setVisibleQuestions(updatedQuestions);
    }
  };

  // Update the free-text answer for the question in local state.
  const handleOtherChange = (questionId, value) => {
    setVisibleQuestions(prev =>
      prev.map(q => {
        if (q.questionId === questionId) {
          return { ...q, selected: value };
        }
        return q;
      })
    );
  };

  // When the user clicks Submit, send an internal message with the appropriate action
  const handleSubmit = () => {
    // Get answers, filtering out any parent/level info we added
    const selections = visibleQuestions.map(({ questionId, question, type, options, selected, isOther }) => ({
      questionId, 
      question, 
      type, 
      options, 
      selected, 
      isOther
    }));
        
    callAction({
      name: submitActionName,
      payload: { selections }
    });
  };

  return (
    <div className="flex flex-col gap-4">
      {visibleQuestions.map((q, index) => (
        <div 
          key={`${q.questionId}-${index}`} 
          className="flex flex-col gap-2"
          style={{ marginLeft: q.level ? `${q.level * 16}px` : '0' }}
        >
          <div className="mb-2 font-medium">
            {q.level > 0 && <span className="text-blue-600">↳ </span>}
            {q.question}
          </div>
          {q.type === "options" ? (
            <Select
              onValueChange={(value) => handleSelectChange(q.questionId, value)}
              value={!q.isOther ? q.selected : ""}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select an option" />
              </SelectTrigger>
              <SelectContent>
                {q.options.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : null}
          {(q.isOther || q.type === "text") && (
            <Input
              value={q.selected}
              placeholder="Enter your answer"
              onChange={(e) => handleOtherChange(q.questionId, e.target.value)}
            />
          )}
        </div>
      ))}
      <Button onClick={handleSubmit}>Submit Answers</Button>
    </div>
  );
}
