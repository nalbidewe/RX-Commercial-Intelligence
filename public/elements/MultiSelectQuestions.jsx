import { useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function MultiSelectQuestions() {
  // Use the globally injected `props` object.
  const initialQuestions = props.questions || [];
  // Local state to manage the questions and their answers.
  const [questionsState, setQuestionsState] = useState(initialQuestions);

  // Update local state when a dropdown selection is made.
  const handleSelectChange = (questionId, value) => {
    setQuestionsState((prev) =>
      prev.map((q) => {
        if (q.questionId === questionId) {
          if (value === "Other (Enter your own)") {
            return { ...q, isOther: true, selected: "" };
          } else {
            return { ...q, isOther: false, selected: value };
          }
        }
        return q;
      })
    );
  };

  // Update the free-text answer for the question in local state.
  const handleOtherChange = (questionId, value) => {
    setQuestionsState((prev) =>
      prev.map((q) => {
        if (q.questionId === questionId) {
          return { ...q, selected: value };
        }
        return q;
      })
    );
  };

  // When the user clicks Submit, send an internal message (with a special marker)
  // so the backend can process the submission silently.
  // In MultiSelectQuestions.jsx
  const handleSubmit = () => {
    callAction({
      name: "submit_selections",
      payload: { selections: questionsState }
    });
  };


  return (
    <div className="flex flex-col gap-4">
      {questionsState.map((q) => (
        <div key={q.questionId} className="flex flex-col gap-2">
          <div className="mb-2 font-medium">{q.question}</div>
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
          {q.isOther && (
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
